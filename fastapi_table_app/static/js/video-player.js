/**
 * 動画再生機能管理ファイル
 * 動画プレイヤーのモーダル表示、動画再生、停止、エラーハンドリングを管理
 * 動画ファイルのストリーミング再生と関連UI操作を含む
 */

// ==================== 動画再生機能 ====================
function playVideo(fullPath, relativePath, device, datetime) {
    const modal = document.getElementById('videoModal');
    const videoPlayer = document.getElementById('video-player');
    const videoSource = document.getElementById('video-source');
    const videoDownload = document.getElementById('video-download');
    
    if (!modal || !videoPlayer || !videoSource) {
        showNotification('動画再生機能の初期化に失敗しました', 'error');
        return;
    }

    // 動画情報を設定
    const deviceElement = document.getElementById('video-device');
    const datetimeElement = document.getElementById('video-datetime');
    const pathElement = document.getElementById('video-path');

    if (deviceElement) deviceElement.textContent = device;
    if (datetimeElement) datetimeElement.textContent = datetime;
    if (pathElement) pathElement.textContent = relativePath;

    // 動画ソースを設定（サーバーの動画配信エンドポイントを使用）
    const videoUrl = `/api/video?path=${encodeURIComponent(relativePath)}`;
    
    // 動画プレーヤーの状態をリセット
    videoPlayer.pause();
    videoPlayer.currentTime = 0;
    videoPlayer.removeAttribute('src');
    videoSource.removeAttribute('src');
    
    // 新しいソースを設定
    videoSource.src = videoUrl;
    videoPlayer.load();
    
    if (videoDownload) {
        videoDownload.href = videoUrl;
        videoDownload.download = datetime;
    }
    
    // モーダルを表示
    modal.style.display = 'block';
    
    // 動画イベントハンドラー
    videoPlayer.onerror = function(e) {
        console.error('動画エラー:', e);
        showNotification('動画の読み込みに失敗しました。ファイルが存在しない可能性があります。', 'error');
        // エラー発生時にモーダルを閉じない
    };

    videoPlayer.onloadstart = function() {
        showNotification('動画を読み込み中...', 'info');
    };

    videoPlayer.oncanplay = function() {
        showNotification('動画の準備が完了しました', 'success');
    };

    videoPlayer.onloadedmetadata = function() {
        const duration = Math.floor(videoPlayer.duration);
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        console.log(`動画時間: ${minutes}分${seconds}秒`);
    };

    // フォーカスを動画プレイヤーに移動
    setTimeout(() => {
        videoPlayer.focus();
    }, 100);
}

// 動画モーダルを閉じる
function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    const videoPlayer = document.getElementById('video-player');
    const videoSource = document.getElementById('video-source');
    
    if (!modal || !videoPlayer || !videoSource) return;

    // 動画を停止して状態をリセット
    videoPlayer.pause();
    videoPlayer.currentTime = 0;
    videoPlayer.removeAttribute('src');
    videoSource.removeAttribute('src');
    
    // モーダルを非表示
    modal.style.display = 'none';
    
    // 通知は表示しない（エラーメッセージと混同しないため）
}