from pathlib import Path
import pytest
import importlib.util
SCRIPT = Path(__file__).resolve().parents[1]/'scripts'/'install_skill.py'
spec = importlib.util.spec_from_file_location('nopc_install_script', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
install, SKILL_NAME = module.install, module.SKILL_NAME


def test_skill_install(tmp_path):
    src=Path(__file__).resolve().parents[1]
    dst=install(src,tmp_path)
    assert dst==(tmp_path/SKILL_NAME)
    assert (dst/'SKILL.md').exists()
    assert (dst/'src'/'nopc_bridge'/'fem3d.py').exists()
    assert not (dst/'runs').exists()
    with pytest.raises(FileExistsError):install(src,tmp_path)
    assert install(src,tmp_path,True)==dst
