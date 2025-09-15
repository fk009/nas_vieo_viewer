/**
 * API通信機能管理ファイル
 * サーバーとの通信、データ更新、フィルタリング結果の取得を管理
 * HTTP通信のエラーハンドリングと非同期処理を含む
 */

// ==================== API通信機能 ====================
async function refreshData() {
    try {
        showNotification('データを更新中...', 'info');

        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        showNotification(`データを更新しました (${result.count}件)`, 'success');

        // ページをリロードしてデータを反映
        setTimeout(() => {
            window.location.reload();
        }, 1500);

    } catch (error) {
        console.error('データ更新エラー:', error);
        showNotification('データ更新に失敗しました', 'error');
    }
}

async function fetchFilteredData(filters = {}) {
    try {
        const params = new URLSearchParams();

        if (filters.devices) params.append('devices', filters.devices.join(','));
        if (filters.categories) params.append('categories', filters.categories.join(','));
        if (filters.startDate) params.append('start_date', filters.startDate);
        if (filters.endDate) params.append('end_date', filters.endDate);

        const response = await fetch(`/api/data?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error('データ取得エラー:', error);
        showNotification('データ取得に失敗しました', 'error');
        return null;
    }
}