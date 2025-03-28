import shutil
import asyncio
from pathlib import Path
from datetime import datetime
import aiofiles
from typing import Optional
from src.utils.logger import get_logger
from .path_info import PathInfo

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class SnapshotManager:
    # 파일 비교를 위한 청크 크기
    _CHUNK_SIZE = 8192  # 8KB
    
    def __init__(self, snapshot_dir: str):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"스냅샷 관리자 초기화 - 경로: {snapshot_dir}")
    
    async def has_changed(self, file_path: str, base_path: str = '/watcher/codes') -> bool:
        """파일 변경 여부 확인"""
        try:
            source = Path(file_path)
            if not source.exists():
                logger.debug(f"파일 없음 - 경로: {file_path}")
                return False
            
            path_info = PathInfo.from_source_path(file_path, base_path=base_path)
            nested_path = path_info._get_nested_path()
            latest_snapshot = self._get_latest_snapshot(source, base_path=base_path)
            
            if not latest_snapshot:
                logger.debug(
                    f"이전 스냅샷 없음 - 원본: {file_path}, "
                    f"스냅샷 경로: {nested_path}"
                )
                return True
            
            # 1. 먼저 파일 크기 비교 (빠른 체크)
            source_size = source.stat().st_size
            snapshot_size = latest_snapshot.stat().st_size
            
            if source_size != snapshot_size:
                logger.debug(
                    f"크기 불일치 - 원본: {source_size}B, "
                    f"스냅샷: {snapshot_size}B, "
                    f"경로: {nested_path}"
                )
                return True
            
            # 2. 파일 크기가 같다면 내용 비교
            logger.debug(f"내용 비교 시작 - 경로: {nested_path}")
            async with aiofiles.open(source, 'rb') as f1, \
                      aiofiles.open(latest_snapshot, 'rb') as f2:
                chunk_count = 0
                while True:
                    chunk1 = await f1.read(self._CHUNK_SIZE)
                    chunk2 = await f2.read(self._CHUNK_SIZE)
                    chunk_count += 1
                    
                    if chunk1 != chunk2:
                        logger.debug(
                            f"내용 불일치 - 청크: {chunk_count}, "
                            f"크기: {self._CHUNK_SIZE}B, 경로: {nested_path}"
                        )
                        return True
                    if not chunk1:  # EOF
                        break
                    
            logger.debug(f"파일 동일 - 청크수: {chunk_count}, 경로: {nested_path}")
            return False
            
        except OSError as e:
            logger.error(f"비교 실패 - 경로: {file_path}, 오류: {str(e)}")
            return False
    
    async def create_snapshot(self, source_path: str, base_path: str = '/watcher/codes') -> str:
        """스냅샷 생성"""
        path_info = PathInfo.from_source_path(source_path, base_path=base_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # hw1 이후의 중첩 경로를 @로 결합하여 저장하도록 수정
        nested_path = path_info._get_nested_path()
        snapshot_path = (self.snapshot_dir / 
                        path_info.class_div / 
                        path_info.hw_name /
                        path_info.student_id /
                        nested_path /
                        f"{timestamp}{Path(source_path).suffix}")
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, source_path, snapshot_path)
            logger.info(f"스냅샷 생성 완료 - 경로: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            logger.error(f"스냅샷 생성 실패 - 오류: {str(e)}")
            raise
            
    async def create_empty_snapshot(self, source_path: str, base_path: str = '/watcher/codes') -> Optional[str]:
        """빈 스냅샷 생성"""
        path_info = PathInfo.from_source_path(source_path, base_path=base_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 최종 스냅샷 경로 생성
        snapshot_path = path_info.get_snapshot_path(self.snapshot_dir, timestamp)
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            # 0바이트 파일 생성
            snapshot_path.touch()
            logger.info(f"빈 스냅샷 생성 완료 - 경로: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            logger.error(f"빈 스냅샷 생성 실패 - 오류: {str(e)}")
            return None

    def _get_snapshot_dir(self, source: Path, base_path: str = '/watcher/codes') -> Path:
        """스냅샷 디렉토리 경로 생성"""
        path_info = PathInfo.from_source_path(str(source), base_path=base_path)
        return path_info.get_snapshot_dir(self.snapshot_dir)

    def _get_latest_snapshot(self, source: Path, base_path: str = '/watcher/codes') -> Optional[Path]:
        """가장 최근 스냅샷 경로 반환"""
        try:
            path_info = PathInfo.from_source_path(str(source), base_path=base_path)
            snapshot_dir = path_info.get_snapshot_dir(self.snapshot_dir)
            
            logger.debug(f"스냅샷 디렉토리 검색 - 경로: {snapshot_dir}")
            
            if not snapshot_dir.exists():
                logger.debug(f"스냅샷 디렉토리 없음 - 경로: {snapshot_dir}")
                return None
            
            # source.suffix는 이미 점(.)을 포함하고 있으므로 그대로 사용
            snapshots = list(snapshot_dir.glob(f"*{source.suffix}"))
            
            if not snapshots:
                logger.debug(f"스냅샷 없음 - 패턴: *{source.suffix}, 경로: {snapshot_dir}")
                return None
            
            latest = max(snapshots, key=lambda p: p.stat().st_mtime)
            logger.debug(
                f"최신 스냅샷 발견 - 경로: {latest}, "
                f"수정시각: {datetime.fromtimestamp(latest.stat().st_mtime)}"
            )
            return latest
            
        except Exception as e:
            logger.error(f"최신 스냅샷 검색 실패 - 오류: {str(e)}")
            return None