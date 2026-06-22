"""
文件名: check_ollama.py
作用: Django 管理命令 —— 检测 Ollama AI 服务健康状态
主要功能:
    1. 检测 Ollama API 连通性
    2. 查询已安装模型列表
    3. 验证目标模型可用性
    4. 执行轻量推理测试
    5. 输出彩色结果摘要到控制台

用法:
    python manage.py check_ollama                 # 检查默认模型 qwen2:7b
    python manage.py check_ollama --model qwen2:7b # 指定模型
"""

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger('apps')


class Command(BaseCommand):
    """
    作用: 手动检测 Ollama 服务健康状态的管理命令
    """

    help = '检测 Ollama AI 服务健康状态（连通性 + 模型可用性 + 推理测试）'

    def add_arguments(self, parser):
        """
        作用: 添加命令行可选参数 --model
        """
        parser.add_argument(
            '--model',
            type=str,
            default=None,
            help='指定要检查的模型名称（默认: qwen2:7b）',
        )

    def handle(self, *args, **options):
        """
        作用: 执行健康检查并输出结果
        """
        from apps.api.services.ai_service import get_ollama_service

        model = options.get('model')
        ollama = get_ollama_service(model=model)

        # 输出检查信息
        self.stdout.write(f'正在检测 Ollama 服务: {ollama.api_url}')
        self.stdout.write(f'目标模型: {ollama.model}')
        self.stdout.write('')

        # 执行健康检查
        result = ollama.check_health()

        # 检测 API 连通性
        if result['api_reachable']:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Ollama API 连通: {ollama.api_url}')
            )
        else:
            self.stderr.write(
                self.style.ERROR(
                    f'[FAIL] 无法连接 Ollama API: {ollama.api_url}'
                )
            )
            self.stderr.write(f'  错误: {result.get("error", "未知错误")}')
            logger.error(
                f'Ollama 健康检查失败: API不可达 '
                f'({result.get("error")})'
            )
            return

        # 显示已安装模型列表
        models = result['available_models']
        if models:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] 已安装模型: {", ".join(models)}')
            )
        else:
            self.stdout.write(
                self.style.WARNING('[WARN] 未检测到任何已安装模型')
            )

        # 检测目标模型可用性
        if result['model_ready']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] 目标模型就绪: {ollama.model}'
                )
            )
        else:
            self.stderr.write(
                self.style.ERROR(
                    f'[FAIL] 目标模型未安装: {ollama.model}'
                )
            )
            available = ', '.join(models) if models else '无'
            self.stderr.write(f'  可用模型: {available}')
            logger.error(
                f'Ollama 健康检查失败: 模型 {ollama.model} 未安装'
            )
            return

        # 执行轻量推理测试
        if result.get('inference_test'):
            elapsed = result.get('inference_time', 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] 模型推理测试通过 (耗时 {elapsed}s)'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'[WARN] 模型推理测试未通过: '
                    f'{result.get("error", "未知原因")}'
                )
            )
            logger.warning(
                f'Ollama 推理测试未通过: {result.get("error")}'
            )

        # 综合结论
        self.stdout.write('')
        if result['healthy']:
            self.stdout.write(self.style.SUCCESS('健康检查通过 ✓'))
            logger.info(
                f'Ollama 健康检查通过: {ollama.api_url}, '
                f'模型: {ollama.model}'
            )
        else:
            self.stderr.write(self.style.ERROR('健康检查未通过 ✗'))
