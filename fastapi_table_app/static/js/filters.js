/**
 * フィルタリング・検索機能管理ファイル（モジュール化版）
 * データのフィルタリング、検索条件の適用、日付範囲指定機能を管理
 * カテゴリ、機器名、日付による絞り込み処理を含む
 */

import { showNotification } from './utils.js';
import { updateVisibleCount } from './table.js';

// ==================== フィルタリング機能（修正版） ====================
export function applyFilters() {
    const categoryCheckboxes = document.querySelectorAll('.category-options input[type="checkbox"]');
    const deviceCheckboxes = document.querySelectorAll('.device-options input[type="checkbox"]');

    // 選択されたカテゴリと機器名を取得
    const selectedCategories = Array.from(categoryCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    const selectedDevices = Array.from(deviceCheckboxes)
        .filter(cb => cb.checked)  
        .map(cb => cb.value);

    const tableRows = document.querySelectorAll('#data-table-body tr');
    let visibleCount = 0;

    tableRows.forEach(row => {
        const device = row.getAttribute('data-device');
        const category = row.getAttribute('data-category');

        // カテゴリフィルタリング（修正：チェックされたもののみ表示）
        const showCategory = selectedCategories.length === 0 || selectedCategories.includes(category);
        // 機器名フィルタリング（修正：チェックされたもののみ表示）
        const showDevice = selectedDevices.length === 0 || selectedDevices.includes(device);

        // 日付フィルターの適用
        const dateCell = row.querySelector('td:nth-child(6)'); // 日付列
        const dateMatch = dateCell ? checkDateFilter(dateCell.textContent.trim()) : true;

        // 表示条件
        const shouldShow = showCategory && showDevice && dateMatch;

        row.style.display = shouldShow ? '' : 'none';
        if (shouldShow) visibleCount++;
    });

    updateVisibleCount(visibleCount); // table.jsから直接参照
    
    // フィルタリング結果の通知
    const totalRows = tableRows.length;
    if (visibleCount !== totalRows) {
        showNotification(`${visibleCount}/${totalRows}件のデータを表示中`);
    }
}

export function checkDateFilter(dateStr) {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;

    if (!startDate && !endDate) return true;
    if (!dateStr) return true;

    try {
        // 日付文字列を比較可能な形式に変換
        const itemDate = dateStr.replace(/\//g, '-');

        if (startDate && itemDate < startDate) return false;
        if (endDate && itemDate > endDate) return false;

        return true;
    } catch (error) {
        console.warn('日付フィルターの処理中にエラーが発生:', error);
        return true;
    }
}

// ==================== 検索・フィルタリング機能（修正版） ====================
export async function handleSearch() {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const startTime = document.getElementById('start-time')?.value;
    const endTime = document.getElementById('end-time')?.value;

    console.log('検索条件:', {
        startDate: startDate,
        endDate: endDate,
        startTime: startTime,
        endTime: endTime
    });

    try {
        showNotification('検索を実行中...', 'info');

        // APIから条件に合致するデータを取得
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        // 現在選択されているカテゴリと機器名も含める
        const selectedCategories = Array.from(document.querySelectorAll('.category-options input[type="checkbox"]:checked'))
            .map(cb => cb.value);
        const selectedDevices = Array.from(document.querySelectorAll('.device-options input[type="checkbox"]:checked'))
            .map(cb => cb.value);

        if (selectedCategories.length > 0) {
            params.append('categories', selectedCategories.join(','));
        }
        if (selectedDevices.length > 0) {
            params.append('devices', selectedDevices.join(','));
        }

        const response = await fetch(`/api/data?${params.toString()}`);
        const data = await response.json();

        if (response.ok) {
            showNotification(`${data.total}件のデータが見つかりました`, 'success');
            
            // ページをリロードして検索結果を表示
            const url = new URL(window.location);
            if (startDate) url.searchParams.set('start_date', startDate);
            if (endDate) url.searchParams.set('end_date', endDate);
            url.searchParams.set('page', '1');

            // 少し遅延を入れてからリロード
            setTimeout(() => {
                window.location.href = url.toString();
            }, 1000);
        } else {
            throw new Error(data.detail || '検索に失敗しました');
        }
    } catch (error) {
        console.error('検索エラー:', error);
        showNotification('検索に失敗しました', 'error');
    }
}

export function navigateToPage(page) {
    const url = new URL(window.location);
    url.searchParams.set('page', page);
    window.location.href = url.toString();
}

export function nextPage() {
    const currentPage = parseInt(new URLSearchParams(window.location.search).get('page') || '1');
    navigateToPage(currentPage + 1);
}

export function previousPage() {
    const currentPage = parseInt(new URLSearchParams(window.location.search).get('page') || '1');
    if (currentPage > 1) {
        navigateToPage(currentPage - 1);
    }
}

export function setupDateInputRestrictions() {
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (startDateInput && endDateInput && availableDates) {
        // 最小日付と最大日付を設定
        const minDate = availableDates[0];
        const maxDate = availableDates[availableDates.length - 1];

        startDateInput.min = minDate;
        startDateInput.max = maxDate;
        endDateInput.min = minDate;
        endDateInput.max = maxDate;

        // 日付変更時のバリデーション
        startDateInput.addEventListener('change', function() {
            if (!availableDates.includes(this.value)) {
                showNotification('選択された日付にはデータが存在しません', 'warning');
                this.value = '';
            }
        });

        endDateInput.addEventListener('change', function() {
            if (!availableDates.includes(this.value)) {
                showNotification('選択された日付にはデータが存在しません', 'warning');
                this.value = '';
            }
        });
    }
}

export async function loadDataInBatches() {
    try {
        // まず最初の100件を取得
        const initialResponse = await fetch('/api/data?limit=100');
        const initialData = await initialResponse.json();
        
        if (initialData.total > 100) {
            showNotification(`データが${initialData.total}件あります。残りを読み込み中...`, 'info');
            
            // 残りのデータをバックグラウンドで取得
            setTimeout(async () => {
                let page = 2;
                while ((page - 1) * 100 < initialData.total) {
                    try {
                        await fetch(`/api/data?page=${page}&limit=100`);
                        page++;
                        
                        // 負荷軽減のため500ms待機
                        await new Promise(resolve => setTimeout(resolve, 500));
                    } catch (error) {
                        console.warn(`ページ${page}の読み込みに失敗:`, error);
                        break;
                    }
                }
                showNotification('全データの読み込みが完了しました', 'success');
            }, 1000);
        }
    } catch (error) {
        console.error('データロードエラー:', error);
    }
}
