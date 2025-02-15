from random import choice
from typing import List, Optional
from asyncio import gather

from httpx import AsyncClient
from nonebot import get_driver
from nonebot.log import logger

from nonebot_plugin_setu_now.utils import download_pic
from nonebot_plugin_setu_now.config import Config
from nonebot_plugin_setu_now.models import Setu, SetuApiData, SetuNotFindError
from nonebot_plugin_setu_now.img_utils import randon_effect
from nonebot_plugin_setu_now.setu_message import SETU_MSG

plugin_config = Config.parse_obj(get_driver().config.dict())
SETU_SIZE = plugin_config.setu_size
API_URL = plugin_config.setu_api_url
REVERSE_PROXY = plugin_config.setu_reverse_proxy
PROXY = plugin_config.setu_proxy
EFFECT = plugin_config.setu_add_randon_effect


class SetuLoader:
    def __init__(
        self,
        size: str = SETU_SIZE,
        api_url: str = API_URL,
        reverse_proxy_url: Optional[str] = REVERSE_PROXY,
        proxy: Optional[str] = PROXY,
    ):
        """
        :说明: `__init__`
        > 初始化

        :可选参数:
          * `size: str = SETU_SIZE`: 图像大小
          * `api_url: str = API_URL`: api地址
          * `reverse_proxy_url: Optional[str] = REVERSE_PROXY`: 图片反向代理地址
          * `proxy: Optional[str] = PROXY`: 代理地址
        """
        self.size = size
        self.api_url = api_url
        self.reverse_proxy_url = reverse_proxy_url
        self.proxy = proxy

    async def get_setu(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[list]] = None,
        r18: bool = False,
        num: int = 1,
    ) -> List[Setu]:
        """
        :说明: `get_setu`
        >

        :可选参数:
          * `keyword: Optional[str] = None`: 关键词
          * `tags: Optional[List[list]] = None`: 标签
          * `r18: bool = False`: r18
          * `num: int = 1`: 数量

        :返回:
          - `List[Setu]`: Setu 对象列表
        """
        setu_list = []
        api_data = await self._get_info_from_setu_api(keyword, tags, r18, num)
        if len(api_data.data) == 0:
            raise SetuNotFindError()

        for setu in api_data.data:
            setu_list.append(Setu(data=setu))
        data = await self._download_img_from_reverse_proxy(setu_list)
        data = self._setu_info_msg(data)
        return data

    async def _get_info_from_setu_api(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[list]] = None,
        r18: bool = False,
        num: int = 1,
    ) -> SetuApiData:
        """
        :说明: `_get_info_from_setu_api`
        > 从API中获取数据

        :可选参数:
          * `keyword: Optional[str] = None`: 关键词
          * `tags: Optional[List[list]] = None`: 标签列表
          * `r18: bool = False`: r18
          * `num: int = 1`: 数量

        :返回:
          - `SetuApiData`: API数据
        """
        data = {
            "keyword": keyword,
            "tag": tags,
            "r18": r18,
            "proxy": self.reverse_proxy_url,
            "num": num,
            "size": self.size,
        }
        headers = {"Content-Type": "application/json"}

        async with AsyncClient(proxies=self.proxy) as client:  # type: ignore
            res = await client.post(
                self.api_url, json=data, headers=headers, timeout=60
            )
        data = res.json()
        logger.debug(f"API返回结果: {data}")

        return SetuApiData(**data)

    async def _download_img_from_reverse_proxy(
        self,
        data: List[Setu],
    ) -> List[Setu]:
        """
        :说明: `_download_img_from_reverse_proxy`
        > 下载图片到 `Setu.img` 中

        :参数:
          * `data: List[Setu]`: Setu 对象列表

        :返回:
          - `List[Setu]`: Setu 对象列表
        """
        tasks = []
        for setu in data:
            logger.debug(f"添加下载任务 {setu.urls}")
            tasks.append(get_pic(setu.urls[self.size]))
        results = await gather(*tasks)
        i = 0
        for setu in data:
            setu.img = results[i]
            i += 1
        return data

    @staticmethod
    def _setu_info_msg(
        data: List[Setu],
    ) -> List[Setu]:
        """
        :说明: `_setu_info_msg`
        > 添加信息到 `Setu.msg` 中

        :参数:
          * `data: List[Setu]`: Setu 对象列表

        :返回:
          - `List[Setu]`: Setu 对象列表
        """
        for setu in data:
            setu.msg = (
                "\n" + choice(SETU_MSG.send) + f"\n标题: {setu.title}\n"
                f"画师: {setu.author}\n"
                f"pid: {setu.pid}"
            )
        return data


async def get_pic(url: str, proxies: Optional[str] = None) -> Optional[bytes]:
    """
    :说明: `get_pic`
    > 获取图片

    :参数:
      * `url: str`: url

    :可选参数:
      * `proxies: Optional[str] = None`: 代理地址

    :返回:
      - `Optional[bytes]`: 图片
    """

    pic = await download_pic(url, proxies)

    if pic:
        if EFFECT:
            return randon_effect(pic).getvalue()
        else:
            return randon_effect(pic, 0).getvalue()
