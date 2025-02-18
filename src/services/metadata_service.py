"""메타데이터 서비스 관련 구현"""
import logging
import aiohttp
from typing import Protocol
from ..models.metadata import SnapshotMetadata

class MetadataService(Protocol):
    """메타데이터 서비스 프로토콜"""
    
    async def register_snapshot(self, metadata: SnapshotMetadata) -> bool:
        """스냅샷 메타데이터를 등록합니다.
        
        Args:
            metadata: 등록할 스냅샷 메타데이터
            
        Returns:
            bool: 등록 성공 여부
        """
        ...

class ApiMetadataService:
    """HTTP API 기반 메타데이터 서비스"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        
    async def register_snapshot(self, metadata: SnapshotMetadata) -> bool:
        """스냅샷 메타데이터를 API 서버에 등록"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/snapshots", json=metadata) as response:
                    if response.status == 200:
                        logging.info(f"메타데이터 등록 성공: {metadata['snapshot_path']}")
                        return True
                    else:
                        logging.error(f"메타데이터 등록 실패: {response.status} - {await response.text()}")
                        return False
        except Exception as e:
            logging.error(f"메타데이터 등록 중 오류 발생: {e}")
            return False 