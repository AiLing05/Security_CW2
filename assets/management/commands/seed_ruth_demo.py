"""Create separate, labelled local demonstration data without changing existing users."""
import base64
import json
import secrets
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from assets.models import User, Asset, AssetVersion, Category, Tag


class Command(BaseCommand):
    help = 'Create Ruth demo accounts/assets; random passwords go only to ignored .env.ruth-demo.'

    def handle(self, *args, **options):
        credentials = Path(settings.BASE_DIR) / '.env.ruth-demo'
        if credentials.exists():
            self.stdout.write('Demo credentials already exist; no users or passwords changed.')
            return
        names = {f'ruth_demo_{name}': role for name, role in [
            ('admin', 'admin'), ('editor', 'editor'), ('other', 'editor'), ('viewer', 'viewer')]}
        if User.objects.filter(username__in=names).exists():
            raise CommandError('A demo username already exists; refusing to overwrite accounts.')
        passwords = {}
        with transaction.atomic():
            users = {}
            for name, role in names.items():
                password = secrets.token_urlsafe(18)
                users[name] = User.objects.create_user(username=name, role=role, password=password)
                passwords[name] = {'role': role, 'password': password}
            category, _ = Category.objects.get_or_create(name='Ruth demo')
            tag, _ = Tag.objects.get_or_create(name='Ruth demo')
            png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
            for name in ['ruth_demo_editor', 'ruth_demo_other']:
                asset = Asset.objects.create(title=f'Ruth demo asset - {name}',
                    description='Local demonstration asset. Approved content is shared.',
                    uploaded_by=users[name], created_by=users[name], category=category,
                    file=ContentFile(png, name='ruth-demo.png'))
                asset.tags.add(tag)
                version = AssetVersion.objects.create(asset=asset, uploaded_by=users[name],
                    file=asset.file.name, version=1, status='approved', title=asset.title,
                    description=asset.description, category=category)
                version.tags.add(tag)
        credentials.write_text(json.dumps(passwords, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Created four demo accounts and two approved assets.'))
        self.stdout.write('Passwords are in ignored .env.ruth-demo. Do not include it in your submission.')
