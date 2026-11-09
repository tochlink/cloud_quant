import os
import tempfile

# 测试中：无条件禁止实盘，数据目录用临时目录
os.environ["QTW_FORBID_LIVE"] = "1"
os.environ.pop("QTW_ALLOW_LIVE_ORDERS", None)
_tmp = tempfile.mkdtemp(prefix="qtw-test-")
os.environ["QTW_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["QTW_OUTPUT_DIR"] = os.path.join(_tmp, "output")
