import React, { useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  Printer,
  Maximize,
  FileText,
  AlertCircle,
  ExternalLink
} from 'lucide-react'

const SimplePdfViewer = ({ 
  pdfUrl, 
  fileName, 
  isDarkMode = false,
  onDownload,
  onPrint,
  onFullscreen,
  zoomLevel = 100,
  onZoomChange
}) => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const iframeRef = useRef(null)

  const handleLoad = () => {
    setLoading(false)
    setError(null)
  }

  const handleError = () => {
    setError('PDF載入失敗')
    setLoading(false)
  }

  const handleZoomIn = () => {
    const newZoom = Math.min((zoomLevel || 100) + 25, 300)
    onZoomChange?.(newZoom)
  }

  const handleZoomOut = () => {
    const newZoom = Math.max((zoomLevel || 100) - 25, 50)
    onZoomChange?.(newZoom)
  }

  const resetZoom = () => {
    onZoomChange?.(100)
  }

  const openInNewTab = () => {
    window.open(pdfUrl, '_blank')
  }

  return (
    <div className={`flex flex-col h-full ${
      isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900'
    }`}>
      {/* PDF工具欄 */}
      <div className={`flex items-center justify-between p-4 border-b ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        {/* 左側 - 文件信息 */}
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${
            isDarkMode ? 'bg-red-600' : 'bg-red-100'
          }`}>
            <FileText className={`h-5 w-5 ${
              isDarkMode ? 'text-white' : 'text-red-600'
            }`} />
          </div>
          <div>
            <h3 className="font-semibold">{fileName || 'PDF文件'}</h3>
            <p className={`text-sm ${
              isDarkMode ? 'text-gray-400' : 'text-gray-500'
            }`}>
              PDF文件預覽
            </p>
          </div>
        </div>

        {/* 中央 - 縮放控制 */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomOut}
            disabled={loading || (zoomLevel || 100) <= 50}
            className={`p-2 rounded-lg transition-colors ${
              loading || (zoomLevel || 100) <= 50
                ? 'opacity-50 cursor-not-allowed'
                : isDarkMode 
                  ? 'hover:bg-gray-700 text-gray-300' 
                  : 'hover:bg-gray-200 text-gray-600'
            }`}
            title="縮小"
          >
            <ZoomOut className="h-4 w-4" />
          </button>

          <button
            onClick={resetZoom}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              isDarkMode 
                ? 'hover:bg-gray-700 text-gray-300' 
                : 'hover:bg-gray-200 text-gray-600'
            }`}
            title="重設縮放"
          >
            {zoomLevel || 100}%
          </button>

          <button
            onClick={handleZoomIn}
            disabled={loading || (zoomLevel || 100) >= 300}
            className={`p-2 rounded-lg transition-colors ${
              loading || (zoomLevel || 100) >= 300
                ? 'opacity-50 cursor-not-allowed'
                : isDarkMode 
                  ? 'hover:bg-gray-700 text-gray-300' 
                  : 'hover:bg-gray-200 text-gray-600'
            }`}
            title="放大"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>

        {/* 右側 - 操作按鈕 */}
        <div className="flex items-center space-x-2">
          <button
            onClick={openInNewTab}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode 
                ? 'hover:bg-gray-700 text-gray-300' 
                : 'hover:bg-gray-200 text-gray-600'
            }`}
            title="在新分頁開啟"
          >
            <ExternalLink className="h-4 w-4" />
          </button>

          {onDownload && (
            <button
              onClick={onDownload}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                loading
                  ? 'opacity-50 cursor-not-allowed'
                  : isDarkMode 
                    ? 'hover:bg-gray-700 text-gray-300' 
                    : 'hover:bg-gray-200 text-gray-600'
              }`}
              title="下載"
            >
              <Download className="h-4 w-4" />
            </button>
          )}

          {onPrint && (
            <button
              onClick={onPrint}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                loading
                  ? 'opacity-50 cursor-not-allowed'
                  : isDarkMode 
                    ? 'hover:bg-gray-700 text-gray-300' 
                    : 'hover:bg-gray-200 text-gray-600'
              }`}
              title="列印"
            >
              <Printer className="h-4 w-4" />
            </button>
          )}

          {onFullscreen && (
            <button
              onClick={onFullscreen}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                loading
                  ? 'opacity-50 cursor-not-allowed'
                  : isDarkMode 
                    ? 'hover:bg-gray-700 text-gray-300' 
                    : 'hover:bg-gray-200 text-gray-600'
              }`}
              title="全螢幕"
            >
              <Maximize className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* PDF內容區域 */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-800 z-10">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-red-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className={`text-lg ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                載入PDF中...
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-800">
            <div className="text-center">
              <AlertCircle className="h-16 w-16 text-red-500 mb-4 mx-auto" />
              <h3 className="text-lg font-semibold mb-2 text-red-500">載入失敗</h3>
              <p className={`text-center mb-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {error}
              </p>
              <button
                onClick={openInNewTab}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                在新分頁開啟
              </button>
            </div>
          </div>
        )}

        {!error && pdfUrl && (
          <iframe
            ref={iframeRef}
            src={`${pdfUrl}#toolbar=1&navpanes=1&scrollbar=1&page=1&view=FitH`}
            className="w-full h-full border-0"
            style={{ 
              transform: `scale(${(zoomLevel || 100) / 100})`,
              transformOrigin: 'top left',
              width: `${100 / ((zoomLevel || 100) / 100)}%`,
              height: `${100 / ((zoomLevel || 100) / 100)}%`
            }}
            onLoad={handleLoad}
            onError={handleError}
            title="PDF預覽"
          />
        )}
      </div>

      {/* 底部提示 */}
      {!loading && !error && (
        <div className={`p-3 border-t text-sm text-center ${
          isDarkMode 
            ? 'bg-gray-800 border-gray-700 text-gray-400' 
            : 'bg-white border-gray-200 text-gray-500'
        }`}>
          使用瀏覽器原生PDF檢視器 • 支援所有標準PDF功能 • 若無法顯示請點擊"在新分頁開啟"
        </div>
      )}
    </div>
  )
}

export default SimplePdfViewer
