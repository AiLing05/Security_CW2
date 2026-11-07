"""Verify only the local, labelled Ruth demo through real HTTP requests.

Requires seed_ruth_demo and the backend. Credentials/tokens are never written
to evidence. This intentionally creates and approves one demo metadata version.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    parsed = urlparse(args.base)
    if parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.username or parsed.password:
        parser.error('This script is restricted to a local demo server.')
    root = Path(__file__).resolve().parents[1]
    accounts = json.loads((root / '.env.ruth-demo').read_text(encoding='utf-8'))
    checks = []

    def call(method, path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(args.base.rstrip('/') + path, method=method, headers=headers,
                          data=json.dumps(data).encode() if data is not None else None)
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                return response.status, json.loads(body) if 'application/json' in response.headers.get('Content-Type', '') else body
        except HTTPError as error:
            return error.code, error.read()

    def record(name, status, expected):
        checks.append({'check': name, 'actual_status': status, 'expected_status': expected,
                       'passed': status == expected})
        if status != expected:
            raise AssertionError(f'{name}: expected {expected}, got {status}')

    tokens = {}
    for name, account in accounts.items():
        status, result = call('POST', '/api/token/', {'username': name, 'password': account['password']})
        record('Login ' + account['role'] + ' ' + name, status, 200)
        tokens[name] = result['access']
    owner, other, admin, viewer = [tokens['ruth_demo_' + name] for name in ['editor', 'other', 'admin', 'viewer']]
    status, listing = call('GET', '/api/assets/', token=owner)
    record('Owner reads asset list', status, 200)
    candidates = listing.get('results', []) if isinstance(listing, dict) else listing
    asset = next(a for a in candidates if a['uploaded_by']['username'] == 'ruth_demo_editor'
                 and a['title'].startswith('Ruth demo'))
    asset_id = asset['id']
    path = f'/api/assets/{asset_id}/'
    record('Anonymous asset read denied', call('GET', path)[0], 401)
    # Editor write endpoints accept multipart/form encoding; send a real multipart body.
    def submit(token, title):
        boundary = 'ruth-demo-boundary'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\n{title}\r\n--{boundary}--\r\n').encode()
        request = Request(args.base.rstrip('/') + path + 'request_update/', data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'Authorization': 'Bearer ' + token})
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, error.read()
    record('Other editor submission denied', submit(other, 'Unauthorized')[0], 403)
    record('Viewer submission denied', submit(viewer, 'Unauthorized')[0], 403)
    status, pending = submit(owner, 'Ruth demo metadata updated')
    record('Owner metadata-only submission accepted', status, 201)
    current = call('GET', path, token=viewer)[1]
    if current['title'] != asset['title'] or current['file'] != asset['file']:
        raise AssertionError('Editor submission changed approved content before review')
    pending_path = f"/api/versions/{pending['id']}/"
    record('Viewer pending metadata denied', call('GET', pending_path, token=viewer)[0], 404)
    record('Other editor pending file denied', call('GET', pending_path + 'file/', token=other)[0], 404)
    record('Viewer role-management denied', call('GET', '/api/users/', token=viewer)[0], 403)
    record('Editor role-management denied', call('GET', '/api/users/', token=owner)[0], 403)
    record('Admin role-management allowed', call('GET', '/api/users/', token=admin)[0], 200)
    record('Admin approves metadata-only request', call('PATCH', pending_path, {'status': 'approved'}, admin)[0], 200)
    final = call('GET', path, token=viewer)[1]
    if final['title'] != 'Ruth demo metadata updated' or final['file'] != asset['file']:
        raise AssertionError('Approval failed to preserve the image and publish the metadata')
    status, content = call('GET', path + 'file/', token=viewer)
    record('Viewer downloads approved asset', status, 200)
    if not content.startswith(b'\x89PNG'):
        raise AssertionError('Downloaded content is not the demo PNG')
    output = root / 'docs/ruth/evidence/live-api-results.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Local labelled Ruth demo only', 'metadata_approval_preserves_file': True,
        'checks': checks}, indent=2), encoding='utf-8')
    print(f'PASS: {len(checks)} live HTTP checks; evidence saved to {output.relative_to(root)}')


if __name__ == '__main__':
    main()
