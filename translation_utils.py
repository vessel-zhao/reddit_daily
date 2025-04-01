from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_tea_util import models as util_models
import logging
import os
from dotenv import load_dotenv

class TranslationUtils:
    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.logger = logging.getLogger(__name__)
        # 加载环境变量
        load_dotenv()
        # 读取翻译开关配置，默认为开启
        self.translation_enabled = os.getenv('TRANSLATION_ENABLED', 'true').lower() == 'true'
        self.logger.info(f"Translation enabled: {self.translation_enabled}")

    def create_client(self) -> alimt20181012Client:
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret
        )
        config.endpoint = 'mt.cn-hangzhou.aliyuncs.com'
        return alimt20181012Client(config)

    def translate(self, text: str) -> str:
        """执行翻译"""
        # 如果翻译功能被禁用，直接返回原文本
        if not self.translation_enabled:
            self.logger.info("Translation is disabled, returning original text")
            return text
            
        client = self.create_client()
        translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
            format_type='text',
            source_language='en',
            target_language='zh',
            source_text=text,
            scene='general'
        )
        runtime = util_models.RuntimeOptions()
        self.logger.info(f"Translating text: {text}")
        try:
            resp = client.translate_general_with_options(translate_general_request, runtime)
            return resp.body.data.translated
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            print(f"Translation error: {e}")
            return text