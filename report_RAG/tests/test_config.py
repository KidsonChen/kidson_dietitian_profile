from pathlib import Path

from src.config import Config


def test_config_loads_env_and_json(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('APP_DEBUG=True\nAPP_LOG_LEVEL=DEBUG\n', encoding='utf-8')

    config = Config(env_file=env_file)
    assert config.APP_DEBUG is True
    assert config.APP_LOG_LEVEL == 'DEBUG'
    assert config.RAW_DATA_DIR == Path(config.BASE_DIR / 'raw_data')
    assert config.MARKDOWN_DIR == Path(config.BASE_DIR / 'md')
    assert config.REPORT_DIR == Path(config.BASE_DIR / 'report')


def test_config_path_creation(tmp_path):
    config = Config(env_file=tmp_path / 'empty.env')
    config.ensure_directories_exist()
    assert config.RAW_DATA_DIR.exists()
    assert config.MARKDOWN_DIR.exists()
    assert config.REPORT_DIR.exists()
    assert config.DATABASE_DIR.exists()
