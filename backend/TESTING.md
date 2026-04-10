# 后端测试与联调脚本

## 自动化测试（pytest）

在 **`backend/`** 目录下安装依赖后执行：

```bash
pip install -r requirements.txt
pytest
```

仅收集 **`tests/`** 目录（见 `pytest.ini` 中 `testpaths`）。单独跑某个文件：

```bash
pytest tests/test_export_docx.py -q
```

`tests/conftest.py` 会在未设置 `SETTINGS_SECRET_KEY` 时为测试进程生成临时 Fernet 密钥，以便导入 `app`；生产环境仍须在 `.env` 中配置真实密钥。

## 本地联调脚本（非 pytest）

位于 **`scripts/`**，需从 **`backend/`** 作为当前目录运行：

| 脚本 | 说明 |
|------|------|
| `python scripts/run_celery_demo.py` | Celery demo + Redis |
| `python scripts/run_kb_search_demo.py` | 知识库检索 |
| `python scripts/run_llm_demo.py` | LLM 调用 |
| `python scripts/run_table_export_demo.py` | 表格导出 Word 示例 |

`tests/test_assembler.py` 也可作为联调入口：`python tests/test_assembler.py [task_id]`。
