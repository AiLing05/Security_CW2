"""Role, ownership, approval and download security regression tests."""
import tempfile
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from assets.models import User, Asset, AssetVersion, Category, Tag


class RBACSecurityTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory(prefix='ruth-rbac-')
        self.addCleanup(self.media.cleanup)
        settings = override_settings(MEDIA_ROOT=self.media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', role='admin')
        self.owner = User.objects.create_user(username='owner', role='editor')
        self.other = User.objects.create_user(username='other', role='editor')
        self.viewer = User.objects.create_user(username='viewer', role='viewer')
        self.category = Category.objects.create(name='Images')
        self.tag = Tag.objects.create(name='Existing')
        self.asset = Asset.objects.create(title='Approved title', description='Approved description',
            uploaded_by=self.owner, category=self.category, file=self.png())
        self.approved = AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner,
            version=1, status='approved', file=self.asset.file.name, title=self.asset.title,
            description=self.asset.description, category=self.category)
        self.pending = AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner,
            version=2, status='pending', file=self.png('pending.png'), title='Secret draft')
        self.rejected = AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner,
            version=3, status='rejected', file=self.png('rejected.png'), title='Rejected draft')

    @staticmethod
    def png(name='original.png'):
        return SimpleUploadedFile(name, b'\x89PNG\r\n\x1a\n' + b'0' * 64, content_type='image/png')

    @staticmethod
    def rows(response):
        return response.data.get('results', []) if isinstance(response.data, dict) else response.data

    def auth(self, user):
        self.client.force_authenticate(user)

    def test_anonymous_cannot_read_or_write_protected_resources(self):
        for path in ['/api/assets/', '/api/categories/', '/api/tags/', '/api/versions/',
                     '/api/users/', f'/api/assets/{self.asset.pk}/file/',
                     f'/api/versions/{self.approved.pk}/file/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_unknown_and_inactive_roles_fail_closed(self):
        for role, active in [('manager', True), ('editor', False)]:
            self.other.role, self.other.is_active = role, active
            self.other.save()
            self.auth(self.other)
            for path in ['/api/assets/', '/api/versions/', '/api/categories/', '/api/tags/']:
                with self.subTest(role=role, active=active, path=path):
                    self.assertEqual(self.client.get(path).status_code, 403)

    def test_only_admin_can_manage_users_including_staff_editor(self):
        self.other.is_staff = True
        self.other.save()
        for user in [self.viewer, self.owner, self.other]:
            self.auth(user)
            for method in ['get', 'post', 'put', 'patch', 'delete']:
                path = '/api/users/' if method == 'post' else f'/api/users/{self.viewer.pk}/'
                with self.subTest(user=user.username, method=method):
                    response = getattr(self.client, method)(path, {'role': 'admin'}, format='json')
                    self.assertEqual(response.status_code, 403)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, 'viewer')
        self.auth(self.admin)  # Application admin need not have Django staff privileges.
        self.assertEqual(self.client.patch(f'/api/users/{self.viewer.pk}/',
                         {'role': 'editor'}, format='json').status_code, 200)

    def test_system_privilege_fields_are_rejected(self):
        self.auth(self.admin)
        for field in ['is_staff', 'is_superuser', 'groups', 'user_permissions']:
            with self.subTest(field=field):
                response = self.client.patch(f'/api/users/{self.viewer.pk}/',
                                             {field: True}, format='json')
                self.assertEqual(response.status_code, 400)

    def test_admin_cannot_remove_own_access_or_modify_superuser(self):
        self.auth(self.admin)
        for data in [{'role': 'viewer'}, {'is_active': False}]:
            self.assertEqual(self.client.patch(f'/api/users/{self.admin.pk}/',
                             data, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/users/{self.admin.pk}/').status_code, 403)
        root = User.objects.create_superuser(username='root')
        self.assertEqual(self.client.patch(f'/api/users/{root.pk}/',
                         {'role': 'viewer'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/users/{root.pk}/').status_code, 403)

    def test_existing_jwt_uses_current_database_role_after_demotion(self):
        token = str(RefreshToken.for_user(self.admin).access_token)
        self.admin.role = 'viewer'
        self.admin.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.get('/api/users/').status_code, 403)

    def test_non_admin_cannot_manage_category_or_tag_dictionary(self):
        for user in [self.owner, self.viewer]:
            self.auth(user)
            for resource, obj in [('categories', self.category), ('tags', self.tag)]:
                for method in ['post', 'put', 'patch', 'delete']:
                    path = f'/api/{resource}/' if method == 'post' else f'/api/{resource}/{obj.pk}/'
                    with self.subTest(user=user.username, resource=resource, method=method):
                        self.assertEqual(getattr(self.client, method)(path, {'name': 'Changed'},
                                         format='json').status_code, 403)

    def test_viewer_cannot_upload_edit_delete_or_submit_version(self):
        self.auth(self.viewer)
        self.assertEqual(self.client.post('/api/assets/', {'file': self.png(), 'title': 'No',
                         'category_id': self.category.pk}, format='multipart').status_code, 403)
        for method in ['put', 'patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(f'/api/assets/{self.asset.pk}/',
                             {'title': 'No'}, format='multipart').status_code, 403)
        self.assertEqual(self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                         {'title': 'No'}, format='multipart').status_code, 403)

    def test_cross_owner_editor_cannot_use_any_write_route(self):
        self.auth(self.other)
        for suffix, method in [('', 'put'), ('', 'patch'), ('', 'delete'), ('request_update/', 'post')]:
            with self.subTest(method=method, suffix=suffix):
                self.assertEqual(getattr(self.client, method)(f'/api/assets/{self.asset.pk}/{suffix}',
                                 {'title': 'No'}, format='multipart').status_code, 403)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, 'Approved title')

    def test_direct_editor_put_and_patch_cannot_bypass_approval(self):
        self.auth(self.owner)
        for method in ['put', 'patch']:
            response = getattr(self.client, method)(f'/api/assets/{self.asset.pk}/',
                         {'title': f'Pending {method}'}, format='multipart')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['status'], 'pending')
            self.asset.refresh_from_db()
            self.assertEqual(self.asset.title, 'Approved title')
        self.assertEqual(self.asset.versions.values('version').distinct().count(), 5)

    def test_parent_upload_route_cannot_target_another_asset(self):
        self.auth(self.other)
        response = self.client.post('/api/assets/', {'title': 'No', 'file': self.png(),
            'parent': self.asset.pk}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.asset.versions.count(), 3)

    def test_server_assigns_upload_owner_and_requires_initial_file(self):
        self.auth(self.owner)
        response = self.client.post('/api/assets/', {'title': 'Upload', 'file': self.png(),
            'category_id': self.category.pk, 'uploaded_by': self.other.pk}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        uploaded = Asset.objects.get(pk=response.data['id'])
        self.assertEqual(uploaded.uploaded_by_id, self.owner.pk)
        self.assertEqual(uploaded.created_by_id, self.owner.pk)
        self.assertEqual(self.client.post('/api/assets/', {'title': 'No file',
            'category_id': self.category.pk}, format='multipart').status_code, 400)

    def test_editor_cannot_create_new_tag_through_asset_submission(self):
        self.auth(self.owner)
        response = self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                                    {'tags': 'Not allowed'}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Tag.objects.filter(name='Not allowed').exists())
        accepted = self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                                    {'tags': self.tag.name}, format='multipart')
        self.assertEqual(accepted.status_code, 201, accepted.data)

    def test_pending_and_rejected_versions_hidden_from_viewers_and_other_editors(self):
        for user in [self.viewer, self.other]:
            self.auth(user)
            response = self.client.get(f'/api/versions/?asset_id={self.asset.pk}')
            self.assertEqual([v['id'] for v in self.rows(response)], [self.approved.pk])
            for version in [self.pending, self.rejected]:
                with self.subTest(user=user.username, version=version.pk):
                    self.assertEqual(self.client.get(f'/api/versions/{version.pk}/').status_code, 404)
                    self.assertEqual(self.client.get(f'/api/versions/{version.pk}/file/').status_code, 404)
            detail = self.client.get(f'/api/assets/{self.asset.pk}/').data
            self.assertEqual([v['id'] for v in detail['versions']], [self.approved.pk])
            self.assertNotIn('email', detail['uploaded_by'])
            listing = self.rows(self.client.get('/api/assets/'))
            self.assertEqual([v['id'] for v in listing[0]['versions']], [self.approved.pk])

    def test_admin_and_owner_can_read_pending_versions(self):
        for user in [self.admin, self.owner]:
            self.auth(user)
            self.assertEqual(self.client.get(f'/api/versions/{self.pending.pk}/').status_code, 200)
            response = self.client.get(f'/api/versions/{self.pending.pk}/file/')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))

    def test_shared_approved_downloads_and_no_raw_media_access(self):
        self.auth(self.viewer)
        for path in [f'/api/assets/{self.asset.pk}/file/', f'/api/versions/{self.approved.pk}/file/']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
        self.assertEqual(self.client.get('/media/' + self.asset.file.name).status_code, 404)

    def test_unapproved_only_asset_hidden_from_unrelated_users(self):
        draft = Asset.objects.create(title='Draft only', uploaded_by=self.owner, file=self.png())
        for user in [self.viewer, self.other]:
            self.auth(user)
            self.assertEqual(self.client.get(f'/api/assets/{draft.pk}/').status_code, 404)
            self.assertEqual(self.client.get(f'/api/assets/{draft.pk}/file/').status_code, 404)
            self.assertNotIn(draft.pk, [a['id'] for a in self.rows(self.client.get('/api/assets/'))])

    def test_version_modification_methods_are_restricted(self):
        for user in [self.viewer, self.owner, self.other]:
            self.auth(user)
            for method in ['post', 'put', 'patch', 'delete']:
                path = '/api/versions/' if method == 'post' else f'/api/versions/{self.pending.pk}/'
                self.assertIn(getattr(self.client, method)(path, {'status': 'approved'},
                              format='json').status_code, [403, 405])
        self.auth(self.admin)
        self.assertEqual(self.client.put(f'/api/versions/{self.pending.pk}/',
                         {'title': 'Overwrite'}, format='json').status_code, 405)
        self.assertEqual(self.client.post('/api/versions/', {}, format='json').status_code, 405)

    def test_admin_approval_is_status_only_and_cannot_reapprove(self):
        self.auth(self.admin)
        url = f'/api/versions/{self.pending.pk}/'
        self.assertEqual(self.client.patch(url, {'status': 'approved', 'title': 'Swap'},
                         format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'status': 'approved'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'status': 'rejected'}, format='json').status_code, 400)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, 'Secret draft')

    def test_out_of_order_approval_cannot_roll_back_newer_content(self):
        newer = AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner,
            version=4, status='pending', file=self.asset.file.name, title='Newest')
        self.auth(self.admin)
        self.assertEqual(self.client.patch(f'/api/versions/{newer.pk}/', {'status': 'approved'},
                         format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/versions/{self.pending.pk}/', {'status': 'approved'},
                         format='json').status_code, 400)

    def test_editor_cannot_access_django_admin_even_with_model_permissions(self):
        from django.contrib.auth.models import Permission
        self.owner.is_staff = True
        self.owner.save()
        self.owner.user_permissions.set(Permission.objects.filter(content_type__app_label='assets'))
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/admin/assets/user/').status_code, 403)
