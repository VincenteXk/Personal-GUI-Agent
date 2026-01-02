# 安装依赖

```bash
uv sync
```

## 激活uv环境

```bash
./.venv/Scripts/activate
```

## 安装 SimpleGraphRAG

```bash
cd simple_graphrag
pip install -e .
```

## 启动后端服务

```bash
cd backend
python main.py
```

## 访问 API 文档

浏览器打开：

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## 启动前端界面

```bash
cd frontend
npm install
npm run dev
```
