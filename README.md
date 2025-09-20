# 1.tongji.icu Mirror - 乌龙茶镜像站

## Examples

API调用示例(可编辑`if True/False`细化单元测试)：

```bash
python -m examples.1_tongji_icu_api_examples
```

Cookie认证测试：

```bash
python -m tests.cookie_auth
```

### 基本使用

#### 1. 测试API连接
```bash
python complete_sync.py --mode test --cookie "your_cookie_string"
```

#### 2. 完整数据同步
```bash
python complete_sync.py --mode full --cookie "your_cookie_string"
```

#### 3. 限制页数测试
```bash
python complete_sync.py --mode full --max-pages 3 --cookie "your_cookie_string"
```

## API端点覆盖

### 用户相关
- `/api/me/` - 用户信息
- `/api/points/` - 用户积分

### 课程相关
- `/api/course/` - 课程列表（支持筛选、排序）
- `/api/course/{id}/` - 课程详情
- `/api/search/` - 课程搜索
- `/api/course-filter/` - 课程筛选选项

### 评价相关
- `/api/review/` - 评价列表
- `/api/review/{id}/` - 评价详情
- `/api/course/{id}/review/` - 课程评价列表
- `/api/review-filter/` - 评价筛选选项

### 基础数据
- `/api/semester/` - 学期列表
- `/api/announcement/` - 公告列表
- `/api/statistic/` - 统计信息
- `/api/common/` - 通用信息

### Cookie获取方法

1. **浏览器开发者工具**：
   - 访问 https://1.tongji.icu
   - 打开开发者工具 (F12)
   - 切换到Network标签
   - 刷新页面
   - 查看请求头中的Cookie字段

2. **浏览器插件**：
   - 使用Cookie导出插件
   - 导出为字符串格式

3. **自动获取**：
   - 工具会尝试自动绕过CloudFlare获取Cookie
   - 支持自动保存和加载

## 🔧 配置选项

### Cookie认证配置
```python
# enhanced_cookie_auth.py
class CookieManager:
    def __init__(self, cookie_file: str = "cookies.json"):
        # Cookie缓存文件路径
        # 过期时间：7天
```

### API客户端配置
```python
# tongji_api_examples.py
class TongjiAPIClient:
    def __init__(self):
        self.base_url = "https://1.tongji.icu"
        self.min_request_interval = 0.5  # 请求间隔
```

### 同步脚本配置
```python
# complete_sync.py
class CompleteSyncManager:
    def __init__(self, output_dir: str = "sync_data"):
        # 输出目录
        # 日志配置
        # 统计信息跟踪
```
