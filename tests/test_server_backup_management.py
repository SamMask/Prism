import os
from pathlib import Path


def _write_backup(
    backup_dir: Path,
    filename: str,
    content: bytes = b'backup',
    mtime: int | None = None,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / filename
    path.write_bytes(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_delete_backup_removes_specific_managed_backup(client, app, tmp_path):
    backup_dir = tmp_path / 'backups'
    app.config['PRISM_BACKUP_DIR'] = str(backup_dir)
    target = _write_backup(backup_dir, 'prism_backup_20260606_120000.db')
    kept = _write_backup(backup_dir, 'prism_backup_20260606_130000.db')

    response = client.delete('/api/server/backup/prism_backup_20260606_120000.db')

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['deleted'] == 'prism_backup_20260606_120000.db'
    assert not target.exists()
    assert kept.exists()


def test_delete_backup_rejects_path_traversal_and_non_managed_names(client, app, tmp_path):
    backup_dir = tmp_path / 'backups'
    app.config['PRISM_BACKUP_DIR'] = str(backup_dir)
    outside = tmp_path / 'outside.db'
    outside.write_bytes(b'outside')

    traversal = client.delete('/api/server/backup/../outside.db')
    arbitrary = client.delete('/api/server/backup/manual.db')

    assert traversal.status_code == 400
    assert arbitrary.status_code == 400
    assert outside.exists()


def test_list_backups_uses_configured_backup_dir(client, app, tmp_path):
    backup_dir = tmp_path / 'backups'
    app.config['PRISM_BACKUP_DIR'] = str(backup_dir)
    _write_backup(backup_dir, 'prism_backup_20260606_120000.db', b'a')

    response = client.get('/api/server/backup/list')

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['count'] == 1
    assert data['data']['backups'][0]['filename'] == 'prism_backup_20260606_120000.db'


def test_download_backup_enforces_default_retention(client, app, tmp_path):
    backup_dir = tmp_path / 'backups'
    app.config['PRISM_BACKUP_DIR'] = str(backup_dir)
    oldest = _write_backup(backup_dir, 'prism_backup_20260601_120000.db', mtime=1)
    kept_mid = _write_backup(backup_dir, 'prism_backup_20260602_120000.db', mtime=2)
    kept_new = _write_backup(backup_dir, 'prism_backup_20260603_120000.db', mtime=3)

    response = client.get('/api/server/backup/download')

    assert response.status_code == 200
    assert response.data
    managed_backups = sorted(backup_dir.glob('prism_backup_*.db'))
    assert len(managed_backups) == 3
    assert not oldest.exists()
    assert kept_mid.exists()
    assert kept_new.exists()


def test_rotate_backups_accepts_keep_alias_for_pi_backup_script(client, app, tmp_path):
    backup_dir = tmp_path / 'backups'
    app.config['PRISM_BACKUP_DIR'] = str(backup_dir)
    old_backups = [
        _write_backup(
            backup_dir,
            f'prism_backup_2026060{i}_120000.db',
            mtime=i,
        )
        for i in range(1, 10)
    ]

    response = client.post('/api/server/backup/rotate', json={'keep': 8})

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert len(data['data']['kept_backups']) == 8
    assert len(data['data']['deleted_backups']) == 2
    assert len(list(backup_dir.glob('prism_backup_*.db'))) == 8
    assert not old_backups[0].exists()
    assert not old_backups[1].exists()
