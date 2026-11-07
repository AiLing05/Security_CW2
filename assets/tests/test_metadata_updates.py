"""Metadata-only updates must preserve the existing file and approval policy."""
from django.test import TestCase
from rest_framework.test import APIClient
from assets.models import User, Asset, AssetVersion, Category


class MetadataOnlyUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', role='admin')
        self.editor = User.objects.create_user(username='editor', role='editor')
        self.viewer = User.objects.create_user(username='viewer', role='viewer')
        self.category = Category.objects.create(name='Images')
        self.asset = Asset.objects.create(title='Original', description='Original description',
            uploaded_by=self.editor, file='assets/existing.png', category=self.category)
        AssetVersion.objects.create(asset=self.asset, uploaded_by=self.editor,
            file=self.asset.file.name, version=1, status='approved', title=self.asset.title,
            description=self.asset.description, category=self.category)
        self.data = {'title': 'New metadata', 'description': 'Updated description',
                     'category_id': str(self.category.pk), 'category': str(self.category.pk)}

    def test_admin_can_patch_metadata_without_file(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f'/api/assets/{self.asset.pk}/', self.data, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.file.name, 'assets/existing.png')
        self.assertEqual(self.asset.title, 'New metadata')
        self.assertEqual(self.asset.latest_version().file.name, 'assets/existing.png')
        self.assertEqual(self.asset.latest_version().title, 'New metadata')

    def test_editor_metadata_only_request_preserves_file_until_approval(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                                    self.data, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        version = AssetVersion.objects.get(pk=response.data['id'])
        self.assertEqual(version.status, 'pending')
        self.assertEqual(version.file.name, 'assets/existing.png')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, 'Original')
        self.client.force_authenticate(self.admin)
        approved = self.client.patch(f'/api/versions/{version.pk}/',
                                     {'status': 'approved'}, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, 'New metadata')
        self.assertEqual(self.asset.file.name, 'assets/existing.png')

    def test_other_editor_cannot_submit_metadata_update(self):
        other = User.objects.create_user(username='other', role='editor')
        self.client.force_authenticate(other)
        response = self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                                    self.data, format='multipart')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.asset.versions.count(), 1)

    def test_viewer_cannot_submit_metadata_update(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.post(f'/api/assets/{self.asset.pk}/request_update/',
                                    self.data, format='multipart')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.asset.versions.count(), 1)
