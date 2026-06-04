# Step 9: 文档上传 + 文本提取 — 执行日志

> **开始日期**: 2026-06-04
> **状态**: ✅ 全部完成，79/79 测试通过 (2026-06-04)

---

## 本次会话完成 (2026-06-04)

### 已创建的文件 (4个)

1. ✅ `backend/app/schemas/document.py` — Document Pydantic 模型
   - `DocumentCreate` — title（可选，默认取文件名）
   - `DocumentUpdate` — title 可选更新
   - `DocumentResponse` — 完整文档数据（含 content 文本内容）
   - `DocumentListResponse` — 分页列表 {items, total, offset, limit}
   - `SUPPORTED_DOCUMENT_TYPES` / `EXT_TO_TYPE` 常量

2. ✅ `backend/app/services/document_service.py` — 文本提取服务
   - `validate_file_type(filename)` — 校验文件类型，返回 file_type
   - `extract_text_from_pdf(file_path)` — PyPDF2 提取 PDF 文本
   - `extract_text_from_markdown(file_path)` — 直接读取 MD 文件
   - `extract_text_from_txt(file_path)` — 直接读取 TXT 文件
   - `extract_text_from_html(file_path)` — BeautifulSoup4 提取 HTML 纯文本
   - `extract_text(file_path, file_type)` — 统一入口，根据类型分发
   - `save_upload_file(upload_file, user_id)` — 保存文件到磁盘，返回 (路径, 类型)
   - `delete_upload_file(file_path)` — 删除磁盘上的文件（尽力而为）

3. ✅ `backend/app/api/v1/documents.py` — 文档路由
   - `POST   /documents` — 上传文档（multipart form: file + title）
   - `GET    /documents` — 分页列表（支持 file_type 过滤，content 截断 200 字符预览）
   - `GET    /documents/{id}` — 文档详情（含完整提取文本，含 403/404 权限校验）
   - `DELETE /documents/{id}` — 删除文档（文件 + 数据库记录，含 403/404 权限校验）

4. ✅ `backend/tests/api/v1/test_documents.py` — 单元测试（23 个用例）
   - TestDocumentUpload (5): TXT/PDF/MD/HTML 上传 + 不传 title 取文件名
   - TestDocumentList (4): 分页列表 / 类型过滤 / 空列表 / content 预览截断
   - TestDocumentDetail (2): 详情获取 / 404 不存在
   - TestDocumentDelete (2): 删除成功 / 404 不存在
   - TestDocumentAuthErrors (2): 无认证 403 / 权限隔离验证
   - TestDocumentValidationErrors (5): 不支持类型 / 空文件 / 无效过滤 / 负offset / limit超限
   - TestDocumentServiceUnit (2): 常量验证 / EXT_TO_TYPE 映射验证

### 已修改的文件 (3个)

5. ✅ `backend/app/main.py` — 导入并注册 documents_router
6. ✅ `backend/requirements.txt` — 添加 `beautifulsoup4==4.12.3`
7. ✅ `docker-compose.yml` — backend 添加 uploads_data 卷挂载 + volumes 声明

### 已更新的文档 (4个)

8. ✅ `docs/PRD_zh.md` — 补充 2.3.2 完整功能描述 + 修正 Step 8 状态 + 章节编号修复
9. ✅ `docs/PRD_en.md` — 同步英文 PRD
10. ✅ `docs/API_zh.md` — 补充 3.2 完整接口文档（4 个端点）
11. ✅ `docs/API_en.md` — 同步英文 API 文档

### 已更新的跟踪文档 (2个)

12. ✅ `PROJECT_TRACKER.md` — 修正 Step 8 状态 + 新增 Step 9 详细指令
13. ✅ `task_logs/step_09_document_upload.md` — 本文件

### Git 记录

- 分支: `feature/step-09-document-upload`（从 `develop` 分出）
- 提交:
  - `09825f0` [Step 9] PRD + API 文档更新：文档上传 + 文本提取
  - `e6fd9ba` [Step 9] 文档上传 + 文本提取：schemas + services + API routes + 单元测试（23个用例）
- 已推送到 origin

---

## 待执行（下次会话）

### Docker 验证步骤

```bash
# 1. 启动 Docker Desktop

# 2. 重建后端镜像（新增 beautifulsoup4 依赖）
docker compose build backend

# 3. 启动所有服务
docker compose up -d

# 4. 检查服务状态
docker compose ps

# 5. 运行数据库迁移（本次无新迁移，但确认最新）
docker compose exec backend alembic upgrade head

# 6. 运行全量测试
docker compose exec backend pytest -v

# 7. 预期结果: 80/80 全部通过
# (Goals 21 + Tasks 24 + WS/Planner 12 + Documents 23)
```

### 手动验证

```bash
# 获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 上传 TXT
echo "这是测试内容" > /tmp/test.txt
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.txt"

# 获取列表
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"

# 查看详情
curl http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN"

# 删除
curl -X DELETE http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Docker 验证 (2026-06-04)

**环境**: Docker Desktop Windows, all services healthy

**过程**:
1. pip install beautifulsoup4 遇到 PyPI SSL 错误 → 切换清华镜像源解决
2. Alembic migration 找不到 4e3d32cdf2c8 → 从 main 分支恢复 Step 8 迁移文件
3. 恢复 Step 8 源码 (planner_agent, ws.py, task model/schema updates)
4. backend 重启 → pytest 全量运行

**测试结果**:
```
======================= 79 passed, 3 warnings in 28.11s ========================
```
- Documents: 22/22 ✅
- Goals: 21/21 ✅
- Tasks: 24/24 ✅
- WS/Planner: 12/12 ✅

### 合并到 develop

```bash
# 测试全部通过后：
git checkout develop
git pull origin develop
git merge feature/step-09-document-upload
git push origin develop
```

---

## 技术笔记

### 架构设计

1. **服务层与路由层分离**: 文本提取逻辑放在 `services/document_service.py`，路由只做请求处理。后续 Step 10（向量嵌入）可以直接复用 `extract_text()`。

2. **尽力而为的文件删除**: `delete_upload_file()` 如果磁盘操作失败只记录 warn 日志、不抛异常。这样即使文件系统出问题，数据库记录依然可以被清理。

3. **列表预览优化**: `GET /documents` 列表中 `content` 截断为前 200 字符，避免传输大文本。完整内容需通过 `GET /documents/{id}` 获取。

4. **文件命名**: 使用 `{user_id}/{uuid}.{ext}` 方式，彻底避免同名冲突。用户隔离则通过目录实现。

### 潜在改进

- 大文件异步处理：当前 50MB 限制下同步处理可行，后续可改为 Celery 异步提取
- 编码检测：非 UTF-8 文本文件可能需要 chardet 自动检测编码
- PDF 提取增强：PyPDF2 对复杂排版支持有限，后续可考虑 pymupdf 或 pdfplumber
