"""
文件名: ai_service.py
作用: AI服务模块（成员A/B共用Ollama）- V2.0
主要功能:
    1. 封装 Ollama /api/generate 生成接口
    2. 封装 Ollama /api/tags 模型列表查询
    3. 提供健康检查（连通性 + 模型就绪 + 推理测试）
    4. 成员A专用：generate_rules() 生成XPath/CSS采集规则
    5. 成员B专用：clean_and_extract() AI清洗与结构化提取
"""

import json
import time
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OllamaService:
    """Ollama本地AI服务封装"""
    
    DEFAULT_API_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen2:7b"
    
    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = api_url or self.DEFAULT_API_URL
        self.model = model or self.DEFAULT_MODEL
    
    def generate(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        作用: 调用 Ollama /api/generate 生成内容
        
        参数:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
        
        返回:
            {
                "success": True/False,
                "response": "生成的内容",
                "model": "模型名称",
                "error": "错误信息"
            }
        """
        try:
            url = f"{self.api_url}/api/generate"
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            }
            
            if system_prompt:
                data["system"] = system_prompt
            
            response = requests.post(url, json=data, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", ""),
                "model": self.model
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Ollama API 超时: {self.api_url}")
            return {"success": False, "error": "AI服务响应超时"}
        except requests.exceptions.ConnectionError:
            logger.error(f"Ollama 连接失败: {self.api_url}")
            return {"success": False, "error": "无法连接到AI服务，请确认Ollama已启动"}
        except Exception as e:
            logger.error(f"Ollama 调用失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_health(self, test_prompt: str = None) -> Dict[str, Any]:
        """
        作用: 检测 Ollama 服务健康状态（API连通性 + 模型可用性 + 推理能力）
        
        参数:
            test_prompt: 推理测试用的提示词（默认: "回复ok"）
        
        返回:
            {
                "healthy": True/False,
                "api_reachable": True/False,
                "model_ready": True/False,
                "available_models": ["模型名", ...],
                "inference_test": True/False/None,
                "inference_time": float,
                "error": str|None
            }
        """
        result = {
            "healthy": False,
            "api_reachable": False,
            "model_ready": False,
            "available_models": [],
            "inference_test": False,
            "inference_time": 0.0,
            "error": None,
        }
        
        # 步骤1: 检测 API 连通性 + 获取模型列表
        models_result = self.list_models()
        if models_result["success"]:
            result["api_reachable"] = True
            result["available_models"] = models_result["models"]
            
            # 步骤2: 检查目标模型是否已安装
            result["model_ready"] = any(
                self.model in m for m in models_result["models"]
            )
        else:
            result["error"] = models_result.get("error", "无法获取模型列表")
            logger.error(f"Ollama 健康检查失败（API连通性）: {result['error']}")
            return result
        
        # 步骤3: 轻量推理测试
        if result["model_ready"]:
            try:
                prompt = test_prompt or "回复ok"
                start = time.time()
                gen_result = self.generate(prompt)
                result["inference_time"] = round(time.time() - start, 2)
                result["inference_test"] = gen_result.get("success", False)
                if not gen_result.get("success"):
                    result["error"] = gen_result.get("error", "推理测试失败")
                    logger.error(f"Ollama 推理测试失败: {result['error']}")
            except Exception as e:
                result["error"] = str(e)
                logger.error(f"Ollama 推理测试异常: {e}")
        
        # 综合判断
        result["healthy"] = result["api_reachable"] and result["model_ready"]
        return result

    def list_models(self) -> Dict[str, Any]:
        """
        作用: 调用 Ollama /api/tags 获取已安装模型列表
        
        返回:
            {"success": True/False, "models": ["模型名", ...], "error": str|None}
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            models = [
                m.get("name", "unknown")
                for m in data.get("models", [])
            ]
            return {"success": True, "models": models, "error": None}
        except requests.exceptions.Timeout:
            logger.error(f"获取 Ollama 模型列表超时: {self.api_url}")
            return {"success": False, "models": [], "error": "获取模型列表超时"}
        except requests.exceptions.ConnectionError:
            logger.error(f"Ollama 连接失败: {self.api_url}")
            return {"success": False, "models": [], "error": "无法连接到Ollama服务"}
        except Exception as e:
            logger.error(f"获取 Ollama 模型列表失败: {str(e)}")
            return {"success": False, "models": [], "error": str(e)}
    
    def generate_rules(self, user_prompt: str, html_skeleton: str) -> Dict[str, Any]:
        """
        成员A专用：生成XPath/CSS采集规则
        
        Args:
            user_prompt: 用户提取指令（如"提取教师姓名、职称"）
            html_skeleton: 精简的DOM结构
        
        Returns:
            {
                "rule_content": "XPath/CSS规则",
                "status": "success/error",
                "error_msg": ""
            }
        """
        system_prompt = """你是一个网页数据采集规则生成专家。根据用户提供的HTML页面结构和提取需求，生成精确的XPath选择器。

要求：
1. 只返回XPath表达式，不要有其他解释
2. 使用相对XPath，避免使用绝对路径
3. 优先使用ID和class属性
4. 如果用户需要提取多个字段，用JSON格式返回

示例输出：
//div[@class='teacher-info']/h3/text()
或
{
    "name": "//div[@class='name']/text()",
    "title": "//span[@class='title']/text()"
}"""
        
        user_content = f"""用户提取需求：{user_prompt}

页面HTML结构：
{html_skeleton[:3000]}

请生成对应的XPath采集规则："""
        
        result = self.generate(user_content, system_prompt)
        
        if result["success"]:
            return {
                "rule_content": result["response"],
                "status": "success",
                "error_msg": ""
            }
        else:
            return {
                "rule_content": "",
                "status": "error",
                "error_msg": result.get("error", "未知错误")
            }
    
    def clean_and_extract(self, markdown: str, user_prompt: str = None) -> Dict[str, Any]:
        """
        成员B专用：清洗Markdown并提取结构化数据
        
        Args:
            markdown: Crawl4AI输出的Markdown内容
            user_prompt: 用户提取指令
        
        Returns:
            {
                "structured_data": {...},
                "cleaned_markdown": "...",
                "status": "success/error"
            }
        """
        system_prompt = """你是一个教育领域数据清洗和结构化提取专家。请从网页内容中提取以下教师信息：

需要提取的字段：
- name: 教师姓名
- title: 职称（教授/副教授/讲师/助教等）
- department: 院系/学院
- email: 电子邮箱
- phone: 联系电话
- research_areas: 研究方向（数组格式）
- profile: 个人简介（精简版）
- education: 教育背景
- publications: 代表性成果（可选）

要求：
1. 只提取明确存在的信息，不要编造
2. 姓名要准确（中文姓名或英文名）
3. 职称识别要准确
4. 邮箱格式要校验
5. 返回标准JSON格式
6. 如果某个字段不存在，返回空字符串或空数组"""
        
        user_content = f"""请从以下网页内容中提取教师信息：

{markdown[:12000]}

请返回JSON格式的结构化数据："""
        
        if user_prompt:
            user_content = f"""用户指定的提取需求：{user_prompt}

网页内容：
{markdown[:12000]}

请按照用户需求提取数据："""
        
        result = self.generate(user_content, system_prompt)
        
        if result["success"]:
            # 尝试解析JSON
            structured_data = {}
            cleaned_markdown = markdown
            
            try:
                response_text = result["response"].strip()
                # 提取JSON部分
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                structured_data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning(f"AI返回非JSON格式: {result['response'][:200]}")
                structured_data = {"_raw_response": result["response"]}
            
            return {
                "structured_data": structured_data,
                "cleaned_markdown": cleaned_markdown,
                "status": "success"
            }
        else:
            return {
                "structured_data": {},
                "cleaned_markdown": markdown,
                "status": "error",
                "error_msg": result.get("error", "AI清洗失败")
            }


# 单例服务实例
_ollama_service = None


def get_ollama_service(api_url: str = None, model: str = None) -> OllamaService:
    """获取Ollama服务单例"""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService(api_url, model)
    return _ollama_service