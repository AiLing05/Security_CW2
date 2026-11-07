"""Authorization regression tests; run only against the isolated test database."""
from django.test import TestCase
from rest_framework.test import APIClient
from assets.models import User, Asset, AssetVersion, Tag


class AuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username='owner', role='editor')
        self.other = User.objects.create_user(username='other', role='editor')
        self.viewer = User.objects.create_user(username='viewer', role='viewer')
        self.asset = Asset.objects.create(title='Original', uploaded_by=self.owner,
                                          file='assets/test.png')

    def test_owner_can_edit_own_asset(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(f'/api/assets/{self.asset.pk}/',
                                     {'title': 'Owner edit'}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, "Original")

    def test_viewer_can_read_shared_approved_asset(self):
        AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner, version=1, status='approved', file=self.asset.file.name)
        self.client.force_authenticate(self.viewer)
        response = self.client.get(f'/api/assets/{self.asset.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_tag(self):
        admin = User.objects.create_user(username='admin', role='admin')
        tag = Tag.objects.create(name='Remove')
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.delete(f'/api/tags/{tag.pk}/').status_code, 204)

    def test_editor_cannot_edit_another_owners_asset(self):
        AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner, version=1, status='approved', file=self.asset.file.name)
        self.client.force_authenticate(self.other)
        response = self.client.patch(f'/api/assets/{self.asset.pk}/',
                                     {'title': 'Unauthorized'}, format='multipart')
        self.assertEqual(response.status_code, 403)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.title, 'Original')

    def test_viewer_cannot_delete_tag(self):
        tag = Tag.objects.create(name='Keep')
        self.client.force_authenticate(self.viewer)
        response = self.client.delete(f'/api/tags/{tag.pk}/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())

    def test_viewer_cannot_delete_version(self):
        version = AssetVersion.objects.create(asset=self.asset, uploaded_by=self.owner,
                                              version=1, file='assets/test.png')
        self.client.force_authenticate(self.viewer)
        response = self.client.delete(f'/api/versions/{version.pk}/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AssetVersion.objects.filter(pk=version.pk).exists())
