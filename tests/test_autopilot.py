import base64
import copy
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from nacl.public import PrivateKey, SealedBox

from autopilot.__main__ import live_settings, main
from autopilot.http import HTTP, RemoteError
from autopilot.instagram import Instagram
from autopilot.pipeline import PendingPublication, Pipeline, weekly_report
from autopilot.render import render
from autopilot.science import Archive, Unverified, validate
from autopilot.simulation import ROW, SimulatedArchive, SimulatedInstagram
from autopilot.state import GitHubState, LocalState, SecretStore, empty_state

NOW = datetime.now(timezone.utc)


def http(handler):
    return HTTP(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)


def renderer(fact, directory):
    path = Path(directory) / 'reel.mp4'
    path.write_bytes(b'fake-video-for-unit-tests')
    return path


def pipeline(tmp_path, ig=None, archive=None, now=None, store=None, secrets=None):
    return Pipeline(store or LocalState(tmp_path / 'ledger.json'), archive or SimulatedArchive(),
                    ig or SimulatedInstagram(), renderer, secrets, now=now or NOW)


@pytest.mark.parametrize('key,value', [
    ('pl_orbper', None), ('pl_orbper', float('nan')), ('pl_orbper', True),
    ('pl_orbpererr1', 0), ('pl_orbpererr2', 1), ('pl_orbpererr1', .2),
    ('pl_controv_flag', 1), ('default_flag', 0), ('pl_orbperlim', 1),
    ('pl_refname', 'a plausible but invented citation'), ('pl_name', "x'; DROP TABLE ps"),
])
def test_science_fail_closed(key, value):
    row = dict(ROW, **{key: value})
    with pytest.raises(Unverified):
        validate(row)


def test_archive_real_contract_and_exact_derivation():
    queries = []
    def handler(request):
        assert request.url.host == 'exoplanetarchive.ipac.caltech.edu'
        queries.append(request.url.params['query'])
        return httpx.Response(200, json=[ROW])
    fact = Archive(http(handler)).select(set())
    assert len(queries) == 2
    assert "pl_name='SIMULATION b'" in queries[1]
    assert '12,0 ore terrestri' in fact['content']['caption']
    assert fact['reference_url'] in ROW['pl_refname']
    assert fact['source_row'] == ROW
    assert len(fact['source_sha256']) == 64


def test_archive_skips_used_or_inconsistent():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[ROW if len(calls) == 1 else dict(ROW, pl_orbper=.6)])
    with pytest.raises(Unverified):
        Archive(http(handler)).select(set())
    calls.clear()
    with pytest.raises(Unverified):
        Archive(http(handler)).select({ROW['pl_name']})
    assert len(calls) == 1


@pytest.mark.parametrize('method,count', [('GET', 3), ('POST', 1)])
def test_retry_only_safe_reads_and_errors_redacted(method, count):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, text='TOP-SECRET')
    with pytest.raises(RemoteError) as exc:
        http(handler).json(method, 'https://graph.instagram.com/me?access_token=TOP-SECRET')
    assert len(calls) == count
    assert 'TOP-SECRET' not in str(exc.value)


def test_instagram_resumable_contract(tmp_path):
    calls = []
    uri = 'https://rupload.facebook.com/ig-api-upload/v24.0/200'
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('/me'):
            return httpx.Response(200, json={'user_id': '100', 'username': 'test'})
        if request.url.path.endswith('/100/media'):
            assert b'upload_type=resumable' in request.content
            return httpx.Response(200, json={'id': '200', 'uri': uri})
        if request.url.host == 'rupload.facebook.com':
            assert request.headers['authorization'] == 'OAuth test-token'
            assert request.headers['file_size'] == '3'
            assert request.content == b'abc'
            return httpx.Response(200, json={'success': True})
        if request.url.path.endswith('/100/media_publish'):
            return httpx.Response(200, json={'id': '300'})
        return httpx.Response(200, json={'status_code': 'FINISHED'})
    ig = Instagram(http(handler), '100', 'test-token', sleep=lambda _: None)
    ig.identity()
    container, destination = ig.create('original caption')
    path = tmp_path / 'video.mp4'
    path.write_bytes(b'abc')
    ig.upload(destination, path)
    assert ig.wait_ready(container) == 'FINISHED'
    assert ig.publish(container) == '300'
    assert len(calls) == 5


@pytest.mark.parametrize('uri', ['https://evil.example/video', 'http://rupload.facebook.com/ig-api-upload/v24.0/200',
                               'https://rupload.facebook.com@evil.example/ig-api-upload/v24.0/200'])
def test_upload_uri_cannot_exfiltrate_credentials(uri):
    ig = Instagram(http(lambda r: httpx.Response(200, json={'id': '200', 'uri': uri})), '100', 'secret')
    with pytest.raises(ValueError):
        ig.create('caption')


def test_identity_mismatch_blocks():
    ig = Instagram(http(lambda r: httpx.Response(200, json={'user_id': '101'})), '100', 'secret')
    with pytest.raises(ValueError):
        ig.identity()


def test_durable_daily_and_subject_deduplication(tmp_path):
    ig = SimulatedInstagram()
    p = pipeline(tmp_path, ig)
    assert p.run(tmp_path) == 'published'
    assert pipeline(tmp_path, ig).run(tmp_path) == 'already_published_today'
    assert pipeline(tmp_path, ig, now=NOW + timedelta(days=1)).run(tmp_path) == 'skipped'
    assert ig.publishes == 1
    assert len(p.store.load()['entries']) == 1
    assert 'Pubblicati: 1' in weekly_report(p.store.load(), NOW + timedelta(days=1))


def test_no_verified_source_never_creates_container(tmp_path):
    class Empty:
        def select(self, used):
            raise Unverified('unknown')
    ig = SimulatedInstagram()
    assert pipeline(tmp_path, ig, archive=Empty()).run(tmp_path) == 'skipped'
    assert ig.publishes == 0
    assert not ig.uploaded


def test_failed_durable_intent_never_publishes(tmp_path):
    class FailingStore(LocalState):
        def save(self, value):
            if any(x['status'] == 'publishing' for x in value['entries']):
                raise RemoteError(409)
            super().save(value)
    ig = SimulatedInstagram()
    p = pipeline(tmp_path, ig, store=FailingStore(tmp_path / 'ledger.json'))
    with pytest.raises(RemoteError):
        p.run(tmp_path)
    assert ig.publishes == 0
    assert p.store.load()['entries'][0]['status'] == 'uploaded'


def test_lost_publish_response_recovers_without_second_publish(tmp_path):
    class Ambiguous(SimulatedInstagram):
        published = False
        def publish(self, container):
            self.publishes += 1
            self.published = True
            raise RemoteError(504)
        def wait_ready(self, container):
            return 'PUBLISHED' if self.published else 'FINISHED'
    ig = Ambiguous()
    with pytest.raises(RemoteError):
        pipeline(tmp_path, ig).run(tmp_path)
    assert pipeline(tmp_path, ig).run(tmp_path) == 'published'
    assert ig.publishes == 1


def test_unresolved_publish_is_not_retried(tmp_path):
    class Ambiguous(SimulatedInstagram):
        def publish(self, container):
            self.publishes += 1
            raise RemoteError(503)
    ig = Ambiguous()
    with pytest.raises(RemoteError):
        pipeline(tmp_path, ig).run(tmp_path)
    with pytest.raises(PendingPublication):
        pipeline(tmp_path, ig).run(tmp_path)
    assert ig.publishes == 1


def test_stale_unpublished_candidate_abandoned(tmp_path):
    p = pipeline(tmp_path)
    state = empty_state()
    fact = SimulatedArchive().select(set())
    fact['checked_at'] = (NOW - timedelta(days=2)).isoformat()
    state['entries'] = [{'date': '2000-01-01', 'fact': fact, 'status': 'prepared'}]
    p.store.save(state)
    assert p.run(tmp_path) == 'skipped'
    assert p.ig.publishes == 0
    assert p.store.load()['entries'][0]['status'] == 'abandoned'


def test_token_refresh_persisted_only_to_secret_store(tmp_path):
    class Refresh(SimulatedInstagram):
        def refresh(self):
            return {'access_token': 'ROTATED-SECRET', 'expires_in': 5184000}
    class Secrets:
        tokens = []
        def save_token(self, token):
            self.tokens.append(token)
    secrets = Secrets()
    p = pipeline(tmp_path, Refresh(), secrets=secrets)
    state = empty_state()
    state['token']['last_refresh'] = (NOW - timedelta(days=8)).isoformat()
    p.store.save(state)
    p.run(tmp_path)
    assert secrets.tokens == ['ROTATED-SECRET']
    assert 'ROTATED-SECRET' not in p.store.path.read_text()
    assert 'expires_at' in p.store.load()['token']


def test_failed_rotation_blocks_publication(tmp_path):
    class Refresh(SimulatedInstagram):
        def refresh(self):
            return {'access_token': 'ROTATED-SECRET', 'expires_in': 5184000}
    class Secrets:
        def save_token(self, token):
            raise RemoteError(403)
    ig = Refresh()
    p = pipeline(tmp_path, ig, secrets=Secrets())
    state = empty_state()
    state['token']['last_refresh'] = (NOW - timedelta(days=8)).isoformat()
    p.store.save(state)
    with pytest.raises(RemoteError):
        p.run(tmp_path)
    assert ig.publishes == 0
    assert p.store.load()['token']['last_refresh'] == state['token']['last_refresh']


def test_github_secret_is_encrypted():
    private = PrivateKey.generate()
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == 'GET':
            return httpx.Response(200, json={'key_id': 'key', 'key': base64.b64encode(bytes(private.public_key)).decode()})
        body = json.loads(request.content)
        assert 'SECRET' not in request.content.decode()
        assert SealedBox(private).decrypt(base64.b64decode(body['encrypted_value'])) == b'SECRET'
        return httpx.Response(204)
    SecretStore(http(handler), 'owner/repo', 'scoped-test-pat').save_token('SECRET')
    assert len(requests) == 2


def test_github_state_uses_compare_and_swap():
    state = empty_state()
    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'sha': 'old-sha', 'content': base64.b64encode(json.dumps(state).encode()).decode()})
        body = json.loads(request.content)
        assert body['sha'] == 'old-sha'
        assert body['branch'] == 'autopilot-state'
        return httpx.Response(409, json={'message': 'conflict'})
    store = GitHubState(http(handler), 'owner/repo', 'workflow-test-token')
    assert store.load() == state
    with pytest.raises(RemoteError):
        store.save(state)


def test_existing_branch_without_ledger_is_not_reset():
    methods = []
    def handler(request):
        methods.append(request.method)
        return httpx.Response(404 if '/contents/' in request.url.path else 200, json={})
    with pytest.raises(ValueError):
        GitHubState(http(handler), 'owner/repo', 'test').load()
    assert methods == ['GET', 'GET']


@pytest.mark.parametrize('enabled,ref', [('false', 'refs/heads/main'), ('true', 'refs/heads/feature')])
def test_live_requires_explicit_optin_and_main(monkeypatch, enabled, ref):
    monkeypatch.setenv('MAD_PUBLISH_ENABLED', enabled)
    monkeypatch.setenv('GITHUB_REF', ref)
    with pytest.raises(ValueError):
        live_settings()


def test_cli_failure_does_not_leak_secrets(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Archive, 'select', lambda *a: (_ for _ in ()).throw(ValueError('TOP-SECRET')))
    assert main(['--mode', 'verify', '--output', str(tmp_path)]) == 1
    assert 'TOP-SECRET' not in capsys.readouterr().err
    assert 'TOP-SECRET' not in (tmp_path / 'report.md').read_text()


def test_complete_offline_e2e_real_video_and_duplicate_guard(tmp_path):
    # Socket access is forbidden by the autouse fixture. No tokens or network needed.
    assert main(['--output', str(tmp_path)]) == 0
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
                             str(tmp_path / 'reel.mp4')], capture_output=True, check=True, text=True)
    info = json.loads(result.stdout)
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height'], video['codec_name']) == (1080, 1920, 'h264')
    assert any(s['codec_name'] == 'aac' for s in info['streams'])
    assert not any(s['codec_type'] == 'subtitle' for s in info['streams'])
    assert next(s for s in info['streams'] if s['codec_type'] == 'audio')['sample_rate'] == '48000'
    assert 19.9 <= float(info['format']['duration']) <= 20.2
    ledger = json.loads((tmp_path / 'simulation-ledger.json').read_text())
    assert len(ledger['entries']) == 1
    assert ledger['entries'][0]['status'] == 'published'
    assert 'SIMULAZIONE' in (tmp_path / 'caption.txt').read_text()
    assert (tmp_path / 'subtitles.srt').stat().st_size > 0
    assert (tmp_path / 'audio-license.txt').exists()
    assert 'Pubblicati: 1' in (tmp_path / 'report.md').read_text()


def test_nasa_unquoted_reference_html_is_supported():
    row = dict(ROW, pl_refname='<a refstr=REAL_FORMAT href=https://ui.adsabs.harvard.edu/abs/SIMULATION-NOT-A-PUBLICATION/abstract target=ref>Test fixture</a>')
    assert validate(row)[1] == 'https://ui.adsabs.harvard.edu/abs/SIMULATION-NOT-A-PUBLICATION/abstract'


def test_large_github_ledger_raw_read_and_concurrency_check():
    calls = []
    def handler(request):
        calls.append(request)
        if request.headers['accept'] == 'application/vnd.github.raw+json':
            return httpx.Response(200, json=empty_state())
        return httpx.Response(200, json={'sha': 'snapshot', 'encoding': 'none', 'content': ''})
    assert GitHubState(http(handler), 'owner/repo', 'test').load() == empty_state()
    assert len(calls) == 3


def test_failure_to_record_success_reconciles_next_run(tmp_path):
    class FailOnce(LocalState):
        fail = True
        def save(self, value):
            if self.fail and any(x['status'] == 'published' for x in value['entries']):
                self.fail = False
                raise RemoteError(500)
            super().save(value)
    class Stateful(SimulatedInstagram):
        def wait_ready(self, container):
            return 'PUBLISHED' if self.publishes else 'FINISHED'
    store = FailOnce(tmp_path / 'ledger.json')
    ig = Stateful()
    with pytest.raises(RemoteError):
        pipeline(tmp_path, ig, store=store).run(tmp_path)
    assert pipeline(tmp_path, ig, store=store).run(tmp_path) == 'published'
    assert ig.publishes == 1
    assert store.load()['entries'][0]['status'] == 'published'


def test_end_to_end_http_adapters_with_persistent_github_state(tmp_path):
    state = empty_state()
    revision = 1
    publishes = 0
    uploads = 0
    def handler(request):
        nonlocal state, revision, publishes, uploads
        if request.url.host == 'exoplanetarchive.ipac.caltech.edu':
            return httpx.Response(200, json=[ROW])
        if request.url.host == 'api.github.com':
            if request.method == 'GET':
                return httpx.Response(200, json={'sha': str(revision), 'encoding': 'base64',
                    'content': base64.b64encode(json.dumps(state).encode()).decode()})
            body = json.loads(request.content)
            assert body['sha'] == str(revision)
            state = json.loads(base64.b64decode(body['content']))
            revision += 1
            return httpx.Response(200, json={'content': {'sha': str(revision)}})
        if request.url.host == 'rupload.facebook.com':
            uploads += 1
            assert request.content == b'fake-video-for-unit-tests'
            return httpx.Response(200, json={'success': True})
        assert request.url.host == 'graph.instagram.com'
        if request.url.path.endswith('/me'):
            return httpx.Response(200, json={'user_id': '100', 'username': 'fixture'})
        if request.url.path.endswith('/100/media'):
            return httpx.Response(200, json={'id': '200', 'uri': 'https://rupload.facebook.com/ig-api-upload/v24.0/200'})
        if request.url.path.endswith('/100/media_publish'):
            assert state['entries'][0]['status'] == 'publishing'
            publishes += 1
            return httpx.Response(200, json={'id': '300'})
        assert request.url.path.endswith('/200')
        return httpx.Response(200, json={'status_code': 'PUBLISHED' if publishes else 'FINISHED'})
    transport = http(handler)
    def run():
        return Pipeline(GitHubState(transport, 'owner/repo', 'test-workflow-token'), Archive(transport),
                        Instagram(transport, '100', 'test-instagram-token'), renderer, now=NOW).run(tmp_path)
    assert run() == 'published'
    assert run() == 'already_published_today'
    assert (publishes, uploads) == (1, 1)
    assert state['entries'][0]['media_id'] == '300'
    assert 'test-instagram-token' not in json.dumps(state)
    assert state['entries'][0]['fact']['source_row'] == ROW
