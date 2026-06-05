from pathlib import Path


def _write_backup(backup_dir: Path, filename: str, content: bytes = b'backup') -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / filename
    path.write_bytes(content)
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
