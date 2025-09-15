"""
接続は　http://localhost:8010
"""



import os
import logging
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mimetypes
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import urllib.parse
from urllib.parse import unquote, quote



# ロギング設定
file_handler = logging.FileHandler('app.log', mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)  # ファイルハンドラーのログレベルをDEBUGに設定

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)  # 標準出力のログレベルをINFOに設定

logging.basicConfig(
    level=logging.DEBUG,  # より詳細なログを出力
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)

# 文字エンコーディングの設定
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# グローバル変数の定義
app = FastAPI(title="監視カメラデータ管理システム")
scanner = None
templates = None

class NASDataScanner:
    """NAS上の監視カメラデータをスキャンするクラス"""
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.category_mapping = {
            "エラーフォルダ": "エラー",
            "その他フォルダ": "その他", 
            "誤検知フォルダ": "誤検知",
            "人物フォルダ": "人物"
        }
        self.cached_data = []
        self.last_scan_time = None
        self.device_pattern = re.compile(r'^came\d{2}$', re.IGNORECASE)  # 大文字小文字を区別しない
        self.year_pattern = re.compile(r'^\d{4}$')  # 年ディレクトリ用
        self.month_pattern = re.compile(r'^\d{2}$')  # 月ディレクトリ用
        self.day_pattern = re.compile(r'^\d{2}$')   # 日ディレクトリ用
        
        logger.info(f"NASDataScanner初期化: base_path={self.base_path}")
        logger.info(f"カテゴリフォルダ設定: {self.category_mapping}")
        logger.debug(f"ベースパスの内容: {[d.name for d in self.base_path.iterdir() if d.is_dir()]}")
        
        # 初期化時にディレクトリの存在を確認
        if not self.base_path.exists():
            logger.error(f"ベースパスが存在しません: {self.base_path}")
            raise FileNotFoundError(f"ベースパスが存在しません: {self.base_path}")
        else:
            logger.info(f"ベースパスの内容: {[d.name for d in self.base_path.iterdir() if d.is_dir()]}")

    def encode_path(self, path: str) -> str:
        """パスを正規化"""
        try:
            if not path:
                logger.error("パスが空です")
                return ""
            
            # パスを正規化（バックスラッシュをスラッシュに変換）
            normalized = str(Path(path)).replace("\\", "/")
            
            # URLエンコード（日本語などの特殊文字を処理）
            encoded = quote(normalized, safe='/:')
            logger.debug(f"パス正規化: {path} -> {encoded}")
            
            return encoded
        except Exception as e:
            logger.error(f"パス正規化エラー: {e}")
            logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
            return path

    def decode_path(self, path: str) -> str:
        """パスを正規化（エンコードされたパスをデコード）"""
        try:
            if not path:
                logger.error("パスが空です")
                return ""
            
            # URLデコード
            decoded = unquote(path, encoding='utf-8')
            
            # パスを正規化
            normalized = str(Path(decoded)).replace("\\", "/")
            logger.debug(f"パス正規化: {path} -> {normalized}")
            
            return normalized
        except Exception as e:
            logger.error(f"パス正規化エラー: {e}")
            logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
            return path

    def get_categories(self) -> List[str]:
        """カテゴリの一覧を取得"""
        return list(self.category_mapping.values())

    def extract_recording_time_from_filename(self, filename: str) -> Optional[float]:
        """ファイル名から撮影時間を抽出してタイムスタンプ（float）を返す"""
        try:
            # ファイル拡張子を除去
            name_without_ext = filename.rsplit('.', 1)[0]
            
            # 正規表現パターン（機器名_年-月-日-時_分_秒-動画番号[_merged_結合番号]）
            pattern = r'^([^_]+)_(\d{4})-(\d{2})-(\d{2})-(\d{2})_(\d{2})_(\d{2})-\d+'
            match = re.match(pattern, name_without_ext)
            
            if match:
                device_name, year, month, day, hour, minute, second = match.groups()
                
                # datetimeオブジェクトを作成
                recording_datetime = datetime(
                    int(year), int(month), int(day), 
                    int(hour), int(minute), int(second)
                )
                
                # タイムスタンプ（float）として返す
                timestamp = recording_datetime.timestamp()
                logger.debug(f"ファイル名解析成功: {filename} -> {recording_datetime}")
                return timestamp
            else:
                logger.warning(f"ファイル名パターンが一致しません: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"ファイル名解析エラー: {filename}, エラー: {e}")
            return None

    def format_timestamp_to_datetime_string(self, timestamp: float) -> str:
        """タイムスタンプを日本語の日時文字列に変換（YYYY年MM月DD日 HH時MM分SS秒）"""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y年%m月%d日 %H時%M分%S秒")
        except:
            return "unknown_time"

    def scan_directories(self) -> List[Dict]:
        """ディレクトリを再帰的にスキャンしてMP4ファイル情報を取得（撮影時間順ソート）"""
        try:
            if not self.base_path.exists():
                logger.warning(f"NASパスが存在しません: {self.base_path}")
                return []

            data = []
            logger.info("ディレクトリスキャン開始")

            # 機器名フォルダを検索
            for device_path in self.base_path.iterdir():
                if not device_path.is_dir():
                    continue

                device_name = device_path.name
                mp4_count = 0

                # 年/月/日のディレクトリを再帰的に検索
                for mp4_file in device_path.rglob("*.mp4"):
                    try:
                        # カテゴリフォルダの確認
                        category_folder = mp4_file.parent
                        if category_folder.name not in self.category_mapping:
                            continue

                        category = self.category_mapping[category_folder.name]
                        
                        # 日付パスの取得（年/月/日）
                        date_parts = mp4_file.relative_to(device_path).parts[:3]
                        if len(date_parts) != 3:
                            continue
                        date_path = "/".join(date_parts)

                        # ファイル名から撮影時間を抽出
                        recording_timestamp = self.extract_recording_time_from_filename(mp4_file.name)
                        
                        if recording_timestamp is not None:
                            datetime_str = self.format_timestamp_to_datetime_string(recording_timestamp)
                            sort_timestamp = recording_timestamp
                        else:
                            # ファイル名から撮影時間を抽出できない場合はファイルの変更時刻を使用
                            file_stat = mp4_file.stat()
                            file_timestamp = file_stat.st_mtime
                            datetime_str = self.format_timestamp_to_datetime_string(file_timestamp)
                            sort_timestamp = file_timestamp
                            logger.warning(f"ファイル名から撮影時間を抽出できないため、ファイル変更時刻を使用: {mp4_file.name}")

                        # txtファイルの存在確認（日付フォルダ直下）
                        date_folder = mp4_file.parent.parent.parent
                        txt_exists = any(f.suffix.lower() == '.txt' for f in date_folder.glob('*.txt'))

                        # 相対パスの生成
                        relative_path = str(mp4_file.relative_to(self.base_path)).replace("\\", "/")

                        data.append({
                            "id": device_name,
                            "datetime": datetime_str,
                            "option": "あり" if txt_exists else "なし",
                            "category": category,
                            "file_path": relative_path,
                            "full_path": str(mp4_file),
                            "date": date_path,
                            "sort_timestamp": sort_timestamp
                        })
                        mp4_count += 1

                    except Exception as e:
                        logger.error(f"ファイル処理エラー {mp4_file}: {e}")
                        continue

                if mp4_count > 0:
                    logger.info(f"機器 {device_name}: {mp4_count}件のMP4ファイル")

            # 撮影時間順でソート
            data.sort(key=lambda x: (x.get("sort_timestamp", 0), x.get("id", "")))

            logger.info(f"総計 {len(data)} 件のMP4ファイルを検出")
            self.cached_data = data
            self.last_scan_time = datetime.now()
            return data

        except Exception as e:
            logger.error(f"ディレクトリスキャンエラー: {e}")
            return []

    def get_devices(self) -> List[str]:
        """機器名の一覧を取得"""
        try:
            devices = [d.name for d in self.base_path.iterdir() 
                      if d.is_dir() and self.device_pattern.match(d.name)]
            return sorted(devices)
        except Exception as e:
            logger.error(f"機器名取得中にエラーが発生: {e}")
            return []

    def get_video_file_path(self, relative_path: str) -> Optional[Path]:
        """相対パスから実際のファイルパスを取得"""
        try:
            full_path = self.base_path / relative_path.replace("\\", "/")
            return full_path if full_path.exists() and full_path.is_file() else None
        except Exception as e:
            logger.error(f"ファイルパス取得エラー: {e}")
            return None

# セキュリティヘッダーの追加
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
static_path = Path(__file__).parent / "static"
if not static_path.exists():
    logger.warning(f"静的ファイルディレクトリが存在しません: {static_path}")
    static_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"静的ファイルディレクトリを作成しました: {static_path}")
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
logger.info(f"静的ファイルディレクトリをマウントしました: {static_path}")

# テンプレートの設定
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
logger.info("テンプレートディレクトリの設定完了")

# NASDataScannerの初期化
try:
    NAS_BASE_PATH = "H:/Nas_Video_Viewer/fastapi_table_app/TEST_NAS"
    logger.info(f"スキャナーの初期化開始: NAS_BASE_PATH={NAS_BASE_PATH}")

    # ディレクトリのアクセス権限を確認
    test_path = Path(NAS_BASE_PATH)
    if not test_path.exists():
        raise FileNotFoundError(f"ディレクトリが存在しません: {NAS_BASE_PATH}")
    if not os.access(NAS_BASE_PATH, os.R_OK):
        raise PermissionError(f"ディレクトリへの読み取りアクセス権がありません: {NAS_BASE_PATH}")
    
    # scannerインスタンスの作成
    scanner = NASDataScanner(NAS_BASE_PATH)
    logger.info("NASDataScannerインスタンスの作成完了")

except Exception as e:
    logger.error(f"スキャナー初期化中にエラーが発生: {e}")
    logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
    raise

# リフレッシュエンドポイントの追加
@app.post("/api/refresh")
async def refresh_data():
    """データを再スキャンして更新"""
    try:
        logger.info("データリフレッシュリクエストを受信")
        if not scanner:
            raise HTTPException(status_code=500, detail="スキャナーが初期化されていません")
        
        # データの再スキャン
        data = scanner.scan_directories()
        logger.info(f"リフレッシュ完了: {len(data)}件のデータを取得")
        
        return {"status": "success", "count": len(data)}
    except Exception as e:
        logger.error(f"リフレッシュ中にエラーが発生: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# データ取得エンドポイントの追加
@app.get("/api/data")
async def get_data(
    device: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """データを取得（フィルタリングとページネーション対応）"""
    try:
        logger.info(f"データリクエスト受信: device={device}, category={category}, start_date={start_date}, end_date={end_date}, page={page}, per_page={per_page}")
        
        # データを取得
        data = scanner.scan_directories()
        if not data:
            logger.warning("データが空です")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "devices": [],
                "categories": []
            }
        
        # フィルタリング
        filtered_data = data
        if device:
            filtered_data = [item for item in filtered_data if item["id"] == device]
        if category:
            filtered_data = [item for item in filtered_data if item["category"] == category]
        if start_date:
            filtered_data = [item for item in filtered_data if item["date"] >= start_date]
        if end_date:
            filtered_data = [item for item in filtered_data if item["date"] <= end_date]
        
        # ページネーション
        total = len(filtered_data)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total)
        
        # 結果を取得
        items = filtered_data[start_idx:end_idx]
        
        # デバイスとカテゴリの一覧を取得
        devices = sorted(list(set(item["id"] for item in data)))
        categories = sorted(list(set(item["category"] for item in data)))
        
        logger.info(f"データ取得完了: {len(items)}件 (合計: {total}件)")
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "devices": devices,
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"データ取得エラー: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="データの取得中にエラーが発生しました")

# 動画取得エンドポイントの追加
@app.get("/api/video")
async def get_video(request: Request, path: str = Query(..., description="動画ファイルの相対パス")):
    """動画ファイルをストリーミング"""
    try:
        logger.info(f"動画リクエスト受信: path={path}")
        
        if not path or path.strip() == "":
            logger.error("動画リクエスト: パスが空です")
            raise HTTPException(status_code=400, detail="動画パスが指定されていません")
        
        # パスをデコードして正規化
        decoded_path = scanner.decode_path(path)
        logger.debug(f"デコードされたパス: {decoded_path}")
        
        if not decoded_path:
            logger.error("動画リクエスト: パスのデコードに失敗しました")
            raise HTTPException(status_code=400, detail="無効な動画パスです")
        
        # 動画ファイルのパスを取得
        video_path = scanner.get_video_file_path(decoded_path)
        if not video_path:
            logger.error(f"動画リクエスト: ファイルが見つかりません: {decoded_path}")
            raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")
        
        logger.info(f"動画ファイルを送信: {video_path}")
        
        # ファイルサイズを取得
        file_size = video_path.stat().st_size
        
        # 範囲リクエストのヘッダーを取得
        range_header = request.headers.get('Range')
        if range_header:
            # 範囲リクエストの処理
            try:
                range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                    
                    if start >= file_size:
                        raise HTTPException(status_code=416, detail="要求された範囲が無効です")
                    
                    chunk_size = 1024 * 1024  # 1MB
                    content_length = end - start + 1
                    
                    async def video_stream():
                        with open(video_path, 'rb') as f:
                            f.seek(start)
                            remaining = content_length
                            while remaining > 0:
                                chunk = min(chunk_size, remaining)
                                data = f.read(chunk)
                                if not data:
                                    break
                                yield data
                                remaining -= len(data)
                    
                    headers = {
                        'Content-Range': f'bytes {start}-{end}/{file_size}',
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(content_length),
                        'Content-Type': 'video/mp4'
                    }
                    return StreamingResponse(
                        video_stream(),
                        status_code=206,
                        headers=headers
                    )
            except ValueError as e:
                logger.error(f"範囲リクエストの処理エラー: {e}")
                raise HTTPException(status_code=400, detail="無効な範囲リクエストです")
        
        # 通常のストリーミング（範囲リクエストなし）
        async def video_stream():
            with open(video_path, 'rb') as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
        
        return StreamingResponse(
            video_stream(),
            media_type='video/mp4',
            headers={
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size)
            }
        )
        
    except HTTPException as he:
        logger.error(f"動画リクエストエラー (HTTP {he.status_code}): {he.detail}")
        raise
    except Exception as e:
        logger.error(f"動画リクエストエラー: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="動画の処理中にエラーが発生しました")

# メインページのルートハンドラー
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """メインページを表示"""
    try:
        logger.info("メインページのリクエストを受信")
        
        # データスキャン
        logger.info("データスキャンを開始")
        table_data = scanner.scan_directories()
        logger.info(f"スキャン結果: {len(table_data)}件のデータを取得")
        
        # デバイスとカテゴリの取得
        devices = scanner.get_devices()
        categories = scanner.get_categories()
        logger.info(f"デバイス: {devices}, カテゴリ: {categories}")
        
        current_time = datetime.now().strftime("%Y年%m月%d日 %H時%M分")
        
        # テンプレート用のコンテキストを作成
        # 一番古い日付を取得
        if table_data:
            oldest_item = min(table_data, key=lambda x: x.get('sort_timestamp', float('inf')))
            try:
                oldest_dt = datetime.fromtimestamp(oldest_item['sort_timestamp'])
                oldest_date = oldest_dt.strftime('%Y年%m月%d日')
            except Exception:
                oldest_date = None
        else:
            oldest_date = None

        context = {
            "request": request,
            "table_data": table_data,
            "devices": devices,
            "categories": categories,
            "current_time": current_time,
            "page_title": "NAS監視カメラデータ管理システム",
            "data_count": len(table_data),
            "last_scan": scanner.last_scan_time.strftime("%Y年%m月%d日 %H時%M分") if scanner.last_scan_time else "未実行",
            "oldest_date": oldest_date
        }
        
        logger.info("テンプレートをレンダリング")
        return templates.TemplateResponse("index.html", context)
        
    except Exception as e:
        logger.error(f"メインページ表示中にエラーが発生: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="システムエラーが発生しました")

# 検索エンドポイントの追加
@app.get("/api/search")
async def search_data(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    start_time: Optional[str] = Query(None, description="開始時間 (HH:MM)"),
    end_time: Optional[str] = Query(None, description="終了時間 (HH:MM)"),
    category: Optional[str] = Query(None, description="カテゴリ（カンマ区切り）"),
    device: Optional[str] = Query(None, description="機器名（カンマ区切り）"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(50, ge=1, le=100, description="1ページあたりの件数")
):
    """日付と時間による検索API（ページネーション対応）"""
    try:
        logger.info(f"検索リクエスト受信: start_date={start_date}, end_date={end_date}, start_time={start_time}, end_time={end_time}, category={category}, device={device}, page={page}, per_page={per_page}")
        
        # データを取得
        data = scanner.scan_directories()
        logger.debug(f"取得したデータ件数: {len(data)}")
        
        if not data:
            logger.warning("データが空です")
            return {
                "status": "success",
                "results": [],
                "count": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0
            }
        
        # 時間オブジェクトの作成（時間指定がある場合のみ）
        start_time_obj = None
        end_time_obj = None
        
        if start_time:
            try:
                start_time_obj = datetime.strptime(start_time, "%H:%M").time()
                logger.debug(f"開始時間: {start_time_obj}")
            except ValueError as e:
                logger.error(f"開始時間のパースエラー: {e}")
                raise HTTPException(status_code=400, detail="無効な開始時間形式です")
        
        if end_time:
            try:
                end_time_obj = datetime.strptime(end_time, "%H:%M").time()
                logger.debug(f"終了時間: {end_time_obj}")
            except ValueError as e:
                logger.error(f"終了時間のパースエラー: {e}")
                raise HTTPException(status_code=400, detail="無効な終了時間形式です")
        
        # フィルタリング
        filtered_data = data
        
        # カテゴリフィルタリング
        if category:
            try:
                categories = [cat.strip() for cat in category.split(',') if cat.strip()]
                filtered_data = [item for item in filtered_data if item.get("category") in categories]
                logger.debug(f"カテゴリでフィルタリング後: {len(filtered_data)}件")
            except Exception as e:
                logger.error(f"カテゴリフィルタリングエラー: {e}")
                raise HTTPException(status_code=400, detail="無効なカテゴリ形式です")
        
        # 機器名フィルタリング
        if device:
            try:
                devices = [dev.strip() for dev in device.split(',') if dev.strip()]
                filtered_data = [item for item in filtered_data if item.get("id") in devices]
                logger.debug(f"機器名でフィルタリング後: {len(filtered_data)}件")
            except Exception as e:
                logger.error(f"機器名フィルタリングエラー: {e}")
                raise HTTPException(status_code=400, detail="無効な機器名形式です")
        
        # 日付フィルタリング（開始日と終了日）
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                start_timestamp = start_date_obj.timestamp()
                filtered_data = [item for item in filtered_data if item.get("sort_timestamp", 0) >= start_timestamp]
                logger.debug(f"開始日でフィルタリング後: {len(filtered_data)}件")
            except ValueError as e:
                logger.error(f"開始日のパースエラー: {e}")
                raise HTTPException(status_code=400, detail="無効な開始日形式です")
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                # 終了日の23時59分59秒までを含める
                end_datetime = datetime.combine(
                    end_date_obj.date(),
                    datetime.max.time().replace(microsecond=0)
                )
                end_timestamp = end_datetime.timestamp()
                filtered_data = [item for item in filtered_data if item.get("sort_timestamp", 0) <= end_timestamp]
                logger.debug(f"終了日でフィルタリング後: {len(filtered_data)}件")
            except ValueError as e:
                logger.error(f"終了日のパースエラー: {e}")
                raise HTTPException(status_code=400, detail="無効な終了日形式です")
        
        # 時間フィルタリング（各日ごとに個別に適用）
        if start_time_obj is not None or end_time_obj is not None:
            time_filtered_data = []
            
            for item in filtered_data:
                try:
                    # アイテムのタイムスタンプから日時を取得
                    item_datetime = datetime.fromtimestamp(item.get("sort_timestamp", 0))
                    item_time = item_datetime.time()
                    
                    # 時間範囲チェック
                    time_in_range = True
                    
                    # 開始時間チェック
                    if start_time_obj is not None:
                        if item_time < start_time_obj:
                            time_in_range = False
                    
                    # 終了時間チェック
                    if end_time_obj is not None:
                        if item_time > end_time_obj:
                            time_in_range = False
                    
                    if time_in_range:
                        time_filtered_data.append(item)
                        
                except Exception as e:
                    logger.warning(f"アイテムの時間処理エラー: {item.get('datetime')}, エラー: {e}")
                    continue
            
            filtered_data = time_filtered_data
            logger.debug(f"時間フィルタリング後: {len(filtered_data)}件")
        
        # 日時でソート（古い順）
        filtered_data.sort(key=lambda x: x.get("sort_timestamp", 0), reverse=False)
        
        # ページネーション
        total = len(filtered_data)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total)
        
        # 結果を取得
        results = filtered_data[start_idx:end_idx]
        
        # フィルタリング後のデータサンプルをログ出力
        if results:
            logger.debug("フィルタリング後のデータサンプル（最初の5件）:")
            for i, item in enumerate(results[:5]):
                logger.debug(f"フィルタリング後データ {i+1}:")
                logger.debug(f"  datetime: {item.get('datetime')}")
                logger.debug(f"  sort_timestamp: {item.get('sort_timestamp')}")
                logger.debug(f"  date: {item.get('date')}")
        
        logger.info(f"検索完了: {len(results)}件のデータを取得 (合計: {total}件, ページ: {page}/{total_pages})")
        
        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
        
    except HTTPException as he:
        raise
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="検索中にエラーが発生しました")

# 存在する日付の一覧を取得するAPIエンドポイント
@app.get("/api/available-dates")
async def get_available_dates():
    """存在する日付の一覧を取得"""
    try:
        logger.info("利用可能な日付の一覧を取得")
        
        # データを取得
        data = scanner.scan_directories()
        if not data:
            logger.warning("データが空です")
            return {
                "status": "success",
                "dates": []
            }
        
        # 日付の一覧を取得（重複を除去）
        available_dates = sorted(list(set(item["date"] for item in data)))
        
        logger.info(f"利用可能な日付: {len(available_dates)}件")
        return {
            "status": "success",
            "dates": available_dates
        }
        
    except Exception as e:
        logger.error(f"日付一覧取得エラー: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="日付一覧の取得中にエラーが発生しました")

# ローカル開発用の起動コード
if __name__ == "__main__":
    try:
        # Windowsでのイベントループポリシーを設定
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # サーバーの設定
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8010,
            reload=True,
            log_level="debug"
        )
        server = uvicorn.Server(config)
        
        # サーバーの起動
        logger.info("サーバーの起動を開始")
        asyncio.run(server.serve())
        
    except KeyboardInterrupt:
        logger.info("アプリケーションを終了します")
    except Exception as e:
        logger.error(f"予期せぬエラーが発生: {e}")
        logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
        sys.exit(1)