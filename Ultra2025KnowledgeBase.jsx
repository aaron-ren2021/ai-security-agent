import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import SimplePdfViewer from './SimplePdfViewer'
import { 
  Send, 
  Sparkles, 
  MessageSquare, 
  BookOpen,
  Target,
  Lightbulb,
  Zap,
  Copy,
  ThumbsUp,
  ArrowUp,
  Bot,
  User,
  Sun,
  Moon,
  Search,
  FileText,
  Plus,
  Upload,
  Download,
  Edit,
  Trash2,
  Filter,
  Tag,
  Calendar,
  Eye,
  History,
  Archive,
  MoreVertical,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  HardDrive
} from 'lucide-react'

const Ultra2025KnowledgeBase = () => {
  // 版本檢測 - 確認新界面已載入
  console.log('🚀 Ultra2025KnowledgeBase 已成功載入！版本：2025.08.28');
  console.log('✨ 新功能：對話歷史管理 + 優化預設問題 + 完美滾動');
  
  // 基本狀態
  const [activeTab, setActiveTab] = useState('chat')
  const [isDarkMode, setIsDarkMode] = useState(false) // 預設淺色模式，與導航欄一致
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  
  // 聊天相關狀態
  const [currentMessages, setCurrentMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chatHistory, setChatHistory] = useState([
    {
      id: 1,
      title: '範疇一排放解析',
      preview: '什麼是範疇一排放？',
      timestamp: new Date('2025-08-27').toISOString(),
      messageCount: 4,
      messages: [
        { 
          type: 'user', 
          content: '什麼是範疇一排放？', 
          timestamp: new Date('2025-08-27 10:30:00').toLocaleString('zh-TW'),
          id: 1001 
        },
        { 
          type: 'assistant', 
          content: '範疇一排放（Scope 1 Emissions）是指企業直接控制或擁有的排放源所產生的溫室氣體排放。這包括：\n\n1. **燃料燃燒**：公司車輛、設備直接燃燒化石燃料\n2. **工業過程**：生產過程中的化學反應\n3. **逸散排放**：設備洩漏、製冷劑逸散等\n\n範疇一排放是企業碳盤查的基礎，也是最容易量化和控制的部分。',
          timestamp: new Date('2025-08-27 10:30:15').toLocaleString('zh-TW'),
          id: 1002,
          sources: [
            {
              title: 'AI碳盤查系統.pdf',
              similarity: 0.89,
              snippet: '範疇一排放包括企業直接控制的排放源...'
            }
          ]
        }
      ]
    },
    {
      id: 2,
      title: 'ISO 14064-1 標準',
      preview: '請介紹ISO 14064-1標準...',
      timestamp: new Date('2025-08-26').toISOString(),
      messageCount: 4,
      messages: [
        { 
          type: 'user', 
          content: '請介紹ISO 14064-1:2018標準', 
          timestamp: new Date('2025-08-26 14:20:00').toLocaleString('zh-TW'),
          id: 2001 
        },
        { 
          type: 'assistant', 
          content: 'ISO 14064-1:2018是國際標準組織制定的溫室氣體量化和報告標準，主要內容包括：\n\n**核心要求：**\n• 設計和開發溫室氣體清冊\n• 確定組織邊界和營運邊界\n• 量化溫室氣體排放和移除\n• 監測、報告和驗證程序\n\n**2018年版本的主要改進：**\n• 更清晰的邊界設定指引\n• 強化的報告要求\n• 改善的不確定性評估方法\n\n這個標準為企業提供了系統性的碳盤查框架。',
          timestamp: new Date('2025-08-26 14:20:25').toLocaleString('zh-TW'),
          id: 2002,
          sources: [
            {
              title: 'ISO 14064-1 碳盤查標準',
              similarity: 0.92,
              snippet: 'ISO 14064-1標準規定了組織層級溫室氣體量化...'
            }
          ]
        }
      ]
    },
    {
      id: 3,
      title: '碳中和策略規劃',
      preview: '企業如何制定碳中和策略？',
      timestamp: new Date('2025-08-25').toISOString(),
      messageCount: 4,
      messages: [
        { 
          type: 'user', 
          content: '企業如何制定碳中和策略？', 
          timestamp: new Date('2025-08-25 16:45:00').toLocaleString('zh-TW'),
          id: 3001 
        },
        { 
          type: 'assistant', 
          content: '企業碳中和策略制定需要系統性方法：\n\n**1. 現狀評估**\n• 完整的碳盤查（範疇1-3）\n• 識別主要排放源\n• 設定基準年\n\n**2. 目標設定**\n• 制定中短期減排目標\n• 設定碳中和時間表\n• 符合科學基礎目標倡議(SBTi)\n\n**3. 減排路徑**\n• 能源效率提升\n• 再生能源轉換\n• 製程優化改善\n• 供應鏈合作\n\n**4. 補償機制**\n• 高品質碳抵換項目\n• 自然碳匯投資\n• 碳捕捉技術\n\n策略成功的關鍵在於循序漸進和持續監測。',
          timestamp: new Date('2025-08-25 16:45:40').toLocaleString('zh-TW'),
          id: 3002,
          sources: [
            {
              title: 'AI碳盤查系統開發總結.pdf',
              similarity: 0.85,
              snippet: '碳中和策略需要包含減排和補償兩個層面...'
            }
          ]
        }
      ]
    }
  ])
  const [activeChatId, setActiveChatId] = useState(null)
  
  // 搜尋和文件狀態
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [documents, setDocuments] = useState([])
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [newDocument, setNewDocument] = useState({
    title: '',
    content: '',
    category: 'general',
    tags: []
  })
  const [sortBy, setSortBy] = useState('newest')
  const [uploading, setUploading] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [notification, setNotification] = useState(null)
  
  // 文件預覽相關狀態（從原始文件完整復制）
  const [previewMode, setPreviewMode] = useState(false)
  const [previewDocument, setPreviewDocument] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(100)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [isFavorite, setIsFavorite] = useState(false)
  const previewRef = useRef(null)
  
  // 文件上傳相關狀態
  const [dragActive, setDragActive] = useState(false)
  const [expandedSources, setExpandedSources] = useState({}) // 展開的引用來源
  
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const chatContainerRef = useRef(null)

  // 2025年最新的預設問題 - 更智能、更個性化
  const intelligentSuggestions = [
    {
      icon: Target,
      title: "範疇分析專家",
      description: "深度解析溫室氣體排放範疇",
      query: "作為碳盤查專家，請詳細說明範疇一、二、三排放的定義、計算方法和實務案例，並提供最新的ISO標準要求。",
      category: "expert",
      color: "from-blue-500 to-cyan-500"
    },
    {
      icon: BookOpen,
      title: "標準解讀助手",
      description: "ISO標準專業解讀",
      query: "請以專業顧問的角度，詳細解讀ISO 14064-1:2018標準的核心要求、實施步驟，以及與舊版本的主要差異。",
      category: "standard",
      color: "from-green-500 to-emerald-500"
    },
    {
      icon: Lightbulb,
      title: "策略規劃顧問",
      description: "碳中和實施路徑規劃",
      query: "作為永續發展顧問，請為我制定一個完整的企業碳中和策略，包括時程規劃、具體行動和投資建議。",
      category: "strategy",
      color: "from-purple-500 to-pink-500"
    },
    {
      icon: Zap,
      title: "計算實務專家",
      description: "碳足跡精準計算",
      query: "請教我如何進行產品碳足跡計算，包括系統邊界設定、數據收集方法、計算公式和結果驗證步驟。",
      category: "calculation",
      color: "from-orange-500 to-red-500"
    }
  ]

  // 文件類別（2025年更新）
  const documentCategories = [
    { value: 'general', label: '通用文件', color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200' },
    { value: 'iso-14064', label: 'ISO 14064', color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' },
    { value: 'iso-14067', label: 'ISO 14067', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
    { value: 'iso-50001', label: 'ISO 50001', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
    { value: 'calculation', label: '計算方法', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
    { value: 'strategy', label: '減碳策略', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
    { value: 'case-study', label: '案例研究', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' }
  ]

  useEffect(() => {
    scrollToBottom()
  }, [currentMessages])

  useEffect(() => {
    if (activeTab === 'knowledge') {
      fetchDocuments()
    }
  }, [activeTab])

  // 從後端載入對話記錄
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        console.log('🔄 載入對話記錄中...')
        const response = await fetch('/api/knowledge/conversations')
        if (response.ok) {
          const data = await response.json()
          console.log('✅ 載入對話記錄成功:', data.conversations?.length || 0, '個對話')
          setChatHistory(data.conversations || [])
        } else {
          console.error('❌ 載入對話記錄失敗:', response.status)
          setChatHistory([])
        }
      } catch (error) {
        console.error('❌ 載入對話記錄錯誤:', error)
        setChatHistory([])
      }
    }
    
    loadChatHistory()
  }, [])

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }

  // 智能 AI 回應格式化函數 - 仿 ChatGPT/Claude 最佳實踐
  const formatAIResponse = (content) => {
    if (!content) return content

    // 如果已經是完整的 HTML，直接返回
    if (content.includes('<table>') && content.includes('<div class="overflow-x-auto">')) {
      return content
    }

    let formatted = content

    // 1. 處理 Markdown 表格格式
    formatted = formatted.replace(/(\|[^|\n]+\|[\s\S]*?\|[^|\n]+\|)/g, (match) => {
      const lines = match.trim().split('\n').filter(line => line.includes('|'))
      if (lines.length < 2) return match

      // 提取表格行
      const rows = lines.map(line => 
        line.split('|').map(cell => cell.trim()).filter(cell => cell && !cell.match(/^[-:\s]+$/))
      ).filter(row => row.length > 0)

      if (rows.length < 2) return match

      const headers = rows[0]
      const dataRows = rows.slice(1)

      return `
        <div class="my-6">
          <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  ${headers.map(header => `
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      ${header}
                    </th>
                  `).join('')}
                </tr>
              </thead>
              <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                ${dataRows.map(row => `
                  <tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    ${row.map(cell => `
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        ${cell}
                      </td>
                    `).join('')}
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `
    })

    // 2. 處理標題（## 標題）
    formatted = formatted.replace(/^## (.+)$/gm, 
      '<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mt-6 mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">$1</h2>'
    )
    formatted = formatted.replace(/^### (.+)$/gm, 
      '<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-5 mb-2">$1</h3>'
    )

    // 3. 處理粗體文字（**文字**）
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, 
      '<strong class="font-semibold text-gray-900 dark:text-gray-100 bg-yellow-100 dark:bg-yellow-900 px-1 rounded">$1</strong>'
    )

    // 4. 處理編號列表（1. 2. 3.）
    formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, (match, num, text) => {
      return `
        <div class="flex items-start space-x-3 my-3">
          <span class="flex-shrink-0 w-7 h-7 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
            ${num}
          </span>
          <span class="flex-1 text-gray-700 dark:text-gray-300 leading-relaxed">${text}</span>
        </div>
      `
    })

    // 5. 處理項目符號列表（• 或 - ）
    formatted = formatted.replace(/^[•\-]\s+(.+)$/gm, 
      '<div class="flex items-start space-x-3 my-2"><span class="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-3"></span><span class="flex-1 text-gray-700 dark:text-gray-300 leading-relaxed">$1</span></div>'
    )

    // 6. 處理特殊符號和表情
    const emojiMap = {
      '📊': '<span class="text-blue-500 mr-1">📊</span>',
      '📝': '<span class="text-green-500 mr-1">📝</span>',
      '📋': '<span class="text-purple-500 mr-1">📋</span>',
      '🔸': '<span class="text-orange-500 mr-1">🔸</span>',
      '✅': '<span class="text-green-500 mr-1">✅</span>',
      '❌': '<span class="text-red-500 mr-1">❌</span>',
      '💡': '<span class="text-yellow-500 mr-1">💡</span>',
      '🎯': '<span class="text-red-500 mr-1">🎯</span>'
    }
    
    Object.entries(emojiMap).forEach(([emoji, html]) => {
      formatted = formatted.replace(new RegExp(emoji, 'g'), html)
    })

    // 7. 處理段落（保持換行結構）
    formatted = formatted.replace(/\n\n/g, '</p><p class="mb-4 text-gray-700 dark:text-gray-300 leading-relaxed">')
    formatted = `<div class="ai-response-formatted space-y-2"><p class="mb-4 text-gray-700 dark:text-gray-300 leading-relaxed">${formatted}</p></div>`

    // 8. 清理多餘的空段落
    formatted = formatted.replace(/<p class="[^"]*">\s*<\/p>/g, '')

    return formatted
  }

  // 創建新對話（調用後端API）
  const createNewChat = async () => {
    try {
      console.log('🔄 創建新對話中...')
      const response = await fetch('/api/knowledge/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: '新對話' })
      })
      
      if (response.ok) {
        const newConversation = await response.json()
        console.log('✅ 創建新對話成功:', newConversation.id)
        
        // 添加到對話記錄
        setChatHistory(prev => [newConversation, ...prev])
        setActiveChatId(newConversation.id)
        setCurrentMessages([])
      } else {
        console.error('❌ 創建對話失敗:', response.status)
        showNotification('error', '創建新對話失敗')
      }
    } catch (error) {
      console.error('❌ 創建對話錯誤:', error)
      showNotification('error', '創建新對話失敗')
    }
  }

  // 上傳文件（完整的原始版本）
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    setUploading(true)
    try {
      for (const file of files) {
        console.log(`🔄 上傳文件: ${file.name}, 類型: ${file.type}, 大小: ${file.size}`)
        
        const formData = new FormData()
        formData.append('file', file)
        
        const response = await fetch('/api/knowledge/upload', {
          method: 'POST',
          body: formData
        })
        
        const responseText = await response.text()
        console.log(`📤 上傳響應 (${file.name}): ${response.status} - ${responseText}`)
        
        if (!response.ok) {
          throw new Error(`上傳 ${file.name} 失敗: ${responseText}`)
        }
        
        const data = JSON.parse(responseText)
        console.log(`✅ 上傳成功 (${file.name}): `, data)
      }
      
      showNotification('success', '文件上傳成功！')
      fetchDocuments()
    } catch (error) {
      console.error('❌ 文件上傳失敗:', error)
      showNotification('error', '文件上傳失敗: ' + error.message)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  // 拖拽處理函數
  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileUpload({ target: { files } })
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragActive(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setDragActive(false)
  }

  // 文件預覽功能（完整的原始版本）
  const openFilePreview = async (document) => {
    console.log('🔍 開始預覽文件:', document)
    setPreviewLoading(true)
    setPreviewMode(true)
    setPreviewDocument(document)
    setZoomLevel(100)
    setCurrentPage(1)
    setIsFullscreen(false)
    
    try {
      // 如果文件沒有內容，嘗試從API獲取
      if (!document.content) {
        console.log('📥 文件沒有內容，嘗試從API獲取:', document.id)
        const response = await fetch(`/api/knowledge/documents/${document.id}`)
        if (response.ok) {
          const data = await response.json()
          console.log('📄 API返回數據:', data)
          if (data.content) {
            document.content = data.content
            setPreviewDocument({...document, content: data.content})
            console.log('✅ 成功設置文件內容，長度:', data.content.length)
          }
        }
      }
    } catch (error) {
      console.error('❌ 預覽文件時發生錯誤:', error)
    } finally {
      setPreviewLoading(false)
    }
  }

  // 關閉文件預覽
  const closePreview = () => {
    setPreviewMode(false)
    setPreviewDocument(null)
    setIsFullscreen(false)
  }

  // 切換全屏
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  // 文件過濾和排序
  const filteredAndSortedDocuments = documents
    .filter(doc => {
      if (searchQuery) {
        return doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
               doc.content?.toLowerCase().includes(searchQuery.toLowerCase())
      }
      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return new Date(a.created_at) - new Date(b.created_at)
        case 'title':
          return a.title.localeCompare(b.title)
        case 'newest':
        default:
          return new Date(b.created_at) - new Date(a.created_at)
      }
    })

  // 刪除文件
  const handleDeleteDocument = async (docId) => {
    try {
      const response = await fetch(`/api/knowledge/documents/${docId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        showNotification('success', '文件已成功刪除')
        fetchDocuments() // 重新載入文件列表
      } else {
        const error = await response.json()
        showNotification('error', `刪除失敗: ${error.error}`)
      }
    } catch (error) {
      console.error('刪除文件失敗:', error)
      showNotification('error', '刪除失敗，請檢查網絡連接')
    }
    setDeleteConfirm(null)
  }

  // 文件預覽相關函數
  const isPdfFile = (filename) => {
    return filename && filename.toLowerCase().endsWith('.pdf')
  }

  const getFileUrl = (fileId) => {
    return `/api/knowledge/documents/${fileId}/preview`  // 使用預覽API而不是下載API
  }

  const downloadFile = () => {
    if (previewDocument) {
      const link = document.createElement('a')
      link.href = `/api/knowledge/documents/${previewDocument.id}/download`  // 下載使用下載API
      link.download = previewDocument.original_name || previewDocument.title
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  const printFile = () => {
    if (previewDocument) {
      const printWindow = window.open(`/api/knowledge/documents/${previewDocument.id}/preview`, '_blank')  // 列印使用預覽API
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print()
        }
      }
    }
  }

  // 顯示通知
  const showNotification = (type, message) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }

  // 保存消息到後端
  const saveMessageToBackend = async (conversationId, type, content, sources = null) => {
    try {
      const response = await fetch(`/api/knowledge/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ type, content, sources })
      })
      
      if (!response.ok) {
        console.error('保存消息失敗:', response.status)
      }
    } catch (error) {
      console.error('保存消息錯誤:', error)
    }
  }

  // 鍵盤事件處理
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      if (activeTab === 'chat') {
        if (e.shiftKey) return
        e.preventDefault()
        handleSendMessage()
      } else if (activeTab === 'search') {
        e.preventDefault()
        handleSearch()
      }
    }
  }

  // 切換對話
  const switchToChat = async (chatId) => {
    try {
      console.log('🔄 切換到對話:', chatId)
      setActiveChatId(chatId)
      
      // 從後端載入對話消息
      const response = await fetch(`/api/knowledge/conversations/${chatId}`)
      if (response.ok) {
        const data = await response.json()
        console.log('✅ 載入對話消息成功:', data.messages?.length || 0, '條消息')
        setCurrentMessages(data.messages || [])
      } else {
        console.error('❌ 載入對話消息失敗:', response.status)
        setCurrentMessages([])
      }
    } catch (error) {
      console.error('❌ 載入對話消息錯誤:', error)
      setCurrentMessages([])
    }
  }

  // 刪除對話（調用後端API）
  const deleteChat = async (chatId) => {
    try {
      console.log('🗑️ 正在刪除對話:', chatId)
      
      const response = await fetch(`/api/knowledge/conversations/${chatId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        console.log('✅ 對話刪除成功')
        
        // 從前端狀態中移除
        setChatHistory(prev => prev.filter(chat => chat.id !== chatId))
        
        // 如果刪除的是當前活動對話，清空當前對話
        if (activeChatId === chatId) {
          setActiveChatId(null)
          setCurrentMessages([])
        }
        
        showNotification('success', '對話已刪除')
      } else {
        console.error('❌ 刪除對話失敗:', response.status)
        const error = await response.json()
        showNotification('error', `刪除失敗: ${error.error || '未知錯誤'}`)
      }
    } catch (error) {
      console.error('❌ 刪除對話錯誤:', error)
      showNotification('error', '刪除對話時發生錯誤')
    }
  }

  // 獲取文件列表
  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/knowledge/documents')
      if (response.ok) {
        const data = await response.json()
        setDocuments(data.documents || [])
      }
    } catch (error) {
      console.error('載入文件失敗:', error)
    }
  }

  // 發送消息（完全重新實現，與後端API整合）
  const handleSendMessage = async (query = inputValue) => {
    if (!query.trim()) return

    setInputValue('')
    setIsLoading(true)

    try {
      let currentConversationId = activeChatId

      // 如果沒有活動對話，創建新對話
      if (!currentConversationId) {
        console.log('🔄 創建新對話...')
        const title = query.substring(0, 30) + (query.length > 30 ? '...' : '')
        const response = await fetch('/api/knowledge/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title })
        })
        
        if (response.ok) {
          const newConversation = await response.json()
          currentConversationId = newConversation.id
          setActiveChatId(currentConversationId)
          
          // 立即重新載入對話記錄
          const conversationsResponse = await fetch('/api/knowledge/conversations')
          if (conversationsResponse.ok) {
            const conversationsData = await conversationsResponse.json()
            setChatHistory(conversationsData.conversations || [])
          }
          
          console.log('✅ 新對話創建成功:', currentConversationId)
        } else {
          throw new Error('創建對話失敗')
        }
      }

      // 創建用戶消息
      const userMessage = {
        type: 'user',
        content: query,
        timestamp: new Date().toLocaleString('zh-TW', {
          year: 'numeric',
          month: '2-digit', 
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        id: Date.now()
      }

      // 立即顯示用戶消息
      setCurrentMessages(prev => [...prev, userMessage])

      // 保存用戶消息到後端
      console.log('💾 保存用戶消息到後端...')
      await saveMessageToBackend(currentConversationId, 'user', query)

      // 調用AI API
      console.log('🤖 調用AI API...')
      const aiResponse = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: query }),
      })

      if (aiResponse.ok) {
        const aiData = await aiResponse.json()
        
        // 創建AI回復消息
        const assistantMessage = {
          type: 'assistant',
          content: aiData.formatted_response?.content || aiData.response,
          timestamp: new Date().toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit', 
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          }),
          id: Date.now() + 1,
          sources: aiData.sources || [],
          performance: aiData.performance
        }

        // 顯示AI回復
        setCurrentMessages(prev => [...prev, assistantMessage])

        // 保存AI回復到後端
        console.log('💾 保存AI回復到後端...')
        await saveMessageToBackend(currentConversationId, 'assistant', aiData.response, aiData.sources)

        // 重新載入對話記錄（更新消息計數等）
        console.log('🔄 重新載入對話記錄...')
        const conversationsResponse = await fetch('/api/knowledge/conversations')
        if (conversationsResponse.ok) {
          const conversationsData = await conversationsResponse.json()
          setChatHistory(conversationsData.conversations || [])
        }

        console.log('✅ 對話完整保存成功')
      } else {
        throw new Error('AI API調用失敗')
      }
    } catch (error) {
      console.error('❌ 發送消息失敗:', error)
      const errorMessage = {
        type: 'assistant',
        content: '抱歉，目前無法處理您的請求。請稍後再試。',
        timestamp: new Date().toLocaleString('zh-TW'),
        id: Date.now() + 1,
        isError: true
      }
      setCurrentMessages(prev => [...prev, errorMessage])
      showNotification('error', '發送消息失敗')
    } finally {
      setIsLoading(false)
    }
  }

  // 處理搜尋
  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setIsSearching(true)
    try {
      const response = await fetch('/api/knowledge/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery })
      })
      
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
      }
    } catch (error) {
      console.error('搜索失敗:', error)
    } finally {
      setIsSearching(false)
    }
  }

  // 添加新文件
  const handleAddDocument = async () => {
    if (!newDocument.title.trim() || !newDocument.content.trim()) {
      alert('請填寫標題和內容')
      return
    }
    
    try {
      const response = await fetch('/api/knowledge/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newDocument)
      })
      
      if (response.ok) {
        setShowAddDialog(false)
        setNewDocument({ title: '', content: '', category: 'general', tags: [] })
        fetchDocuments()
        alert('文件添加成功！')
      } else {
        const error = await response.json()
        alert('添加失敗: ' + error.error)
      }
    } catch (error) {
      console.error('添加文件失敗:', error)
      alert('添加失敗: ' + error.message)
    }
  }

  const handleSuggestionClick = (query) => {
    setActiveTab('chat')
    setInputValue(query)
    handleSendMessage(query)
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  const getCategoryInfo = (category) => {
    return documentCategories.find(cat => cat.value === category) || documentCategories[0]
  }

  const formatDate = (dateString) => {
    if (!dateString) return '未知時間'
    
    try {
      // 處理後端返回的時間格式 (YYYY-MM-DD HH:MM:SS)
      const date = new Date(dateString.replace(' ', 'T') + (dateString.includes('T') ? '' : ''))
      
      if (isNaN(date.getTime())) {
        console.error('無效的日期格式:', dateString)
        return '無效日期'
      }
      
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays === 1) return '今天'
      if (diffDays === 2) return '昨天'
      if (diffDays <= 7) return `${diffDays} 天前`
      
      // 返回格式化的日期
      return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      })
    } catch (error) {
      console.error('日期解析錯誤:', error, dateString)
      return '日期錯誤'
    }
  }

  return (
    <div className={`min-h-screen transition-all duration-300 ${
      isDarkMode 
        ? 'bg-gray-900 text-white' 
        : 'bg-gray-50 text-gray-900'
    }`}>
      {/* 2025年最新布局 - 側邊欄 + 主內容 */}
      <div className="flex h-screen">
        
        {/* 左側邊欄 - ChatGPT風格對話歷史 */}
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex flex-col border-r ${
                isDarkMode 
                  ? 'bg-gray-900 border-gray-700' 
                  : 'bg-white border-gray-200'
              }`}
            >
              {/* 側邊欄頭部 */}
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <div className={`p-2 rounded-lg ${
                      isDarkMode ? 'bg-emerald-600' : 'bg-emerald-500'
                    }`}>
                      <Sparkles className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-sm">碳盤查助手</h2>
                      <p className={`text-xs ${
                        isDarkMode ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        AI 知識庫
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setSidebarCollapsed(true)}
                    className={`p-1.5 rounded transition-colors ${
                      isDarkMode 
                        ? 'hover:bg-gray-800 text-gray-400' 
                        : 'hover:bg-gray-100 text-gray-600'
                    }`}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
                
                <button
                  onClick={createNewChat}
                  className={`w-full flex items-center justify-center space-x-2 px-3 py-2.5 rounded-lg transition-colors ${
                    isDarkMode 
                      ? 'bg-gray-800 hover:bg-gray-700 text-gray-200' 
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  }`}
                >
                  <Plus className="h-4 w-4" />
                  <span className="text-sm font-medium">新對話</span>
                </button>
              </div>

              {/* 對話歷史列表 */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {chatHistory.map((chat) => (
                  <motion.div
                    key={chat.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`group relative p-3 rounded-lg cursor-pointer transition-all ${
                      activeChatId === chat.id
                        ? isDarkMode 
                          ? 'bg-gray-800 border border-gray-600' 
                          : 'bg-emerald-50 border border-emerald-200'
                        : isDarkMode
                          ? 'hover:bg-gray-800'
                          : 'hover:bg-gray-100'
                    }`}
                    onClick={() => switchToChat(chat.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium truncate">
                          {chat.title}
                        </h3>
                        <p className={`text-xs mt-1 truncate ${
                          isDarkMode ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {chat.preview || (chat.message_count > 0 ? '點擊查看對話內容' : '開始新的對話...')}
                        </p>
                        <div className={`flex items-center space-x-2 mt-2 text-xs ${
                          isDarkMode ? 'text-gray-500' : 'text-gray-500'
                        }`}>
                          <span>{formatDate(chat.created_at || chat.timestamp)}</span>
                          <span>•</span>
                          <span>{chat.message_count || chat.messageCount || 0} 條消息</span>
                        </div>
                      </div>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteChat(chat.id)
                        }}
                        className={`opacity-0 group-hover:opacity-100 p-1 rounded transition-all ${
                          isDarkMode 
                            ? 'hover:bg-gray-700 text-gray-400' 
                            : 'hover:bg-gray-200 text-gray-500'
                        }`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* 底部設置 */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setIsDarkMode(!isDarkMode)}
                  className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                    isDarkMode 
                      ? 'hover:bg-gray-800 text-gray-300' 
                      : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                  <span className="text-sm">{isDarkMode ? '淺色模式' : '深色模式'}</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 側邊欄收起時的展開按鈕 */}
        {sidebarCollapsed && (
          <div className="w-12 flex flex-col items-center justify-start pt-4 border-r border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setSidebarCollapsed(false)}
              className={`p-2 rounded-lg transition-colors ${
                isDarkMode 
                  ? 'hover:bg-gray-800 text-gray-400' 
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        )}

        {/* 主內容區域 */}
        <div className="flex-1 flex flex-col">
          {/* 頂部導航 */}
          <div className={`border-b ${
            isDarkMode 
              ? 'border-gray-700 bg-gray-900' 
              : 'border-gray-200 bg-white'
          }`}>
            <div className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold">
                    {activeTab === 'chat' ? '智能對話' :
                     activeTab === 'search' ? '知識搜尋' :
                     activeTab === 'documents' ? '文件瀏覽' : '文件管理'}
                  </h1>
                  <p className={`text-sm mt-1 ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-600'
                  }`}>
                    {activeTab === 'chat' ? '與AI助手對話，獲得專業碳盤查知識' :
                     activeTab === 'search' ? '搜尋知識庫中的專業文件' :
                     activeTab === 'documents' ? '瀏覽所有知識文件' : '管理知識庫文件'}
                  </p>
                </div>
              </div>

              {/* 功能標籤 */}
              <div className="flex space-x-1 mt-6">
                {[
                  { id: 'chat', label: 'AI對話', icon: MessageSquare },
                  { id: 'knowledge', label: '知識庫管理', icon: BookOpen }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-6 py-3 rounded-lg transition-all ${
                      activeTab === tab.id
                        ? isDarkMode 
                          ? 'bg-emerald-600 text-white' 
                          : 'bg-emerald-500 text-white'
                        : isDarkMode
                          ? 'hover:bg-gray-800 text-gray-300'
                          : 'hover:bg-gray-100 text-gray-600'
                    }`}
                  >
                    <tab.icon className="h-5 w-5" />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 內容區域 */}
          <div className="flex-1 overflow-hidden">
            
            {/* AI對話標籤 */}
            {activeTab === 'chat' && (
              <div className="h-full flex flex-col">
                {/* 對話內容區域 */}
                <div 
                  ref={chatContainerRef}
                  className="flex-1 overflow-y-auto px-6 py-6 space-y-6"
                  style={{ maxHeight: 'calc(100vh - 200px)' }}
                >
                  {currentMessages.length === 0 ? (
                    /* 歡迎界面 - 2025年最新設計 */
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="max-w-4xl mx-auto text-center py-12"
                    >
                      <div className={`inline-flex p-4 rounded-2xl mb-8 bg-gradient-to-r ${
                        isDarkMode ? 'from-blue-600 to-purple-600' : 'from-blue-500 to-purple-500'
                      }`}>
                        <Bot className="h-12 w-12 text-white" />
                      </div>
                      
                      <h2 className="text-3xl font-bold mb-4 bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                        歡迎使用 AI 碳盤查專家
                      </h2>
                      
                      <p className={`text-lg mb-12 max-w-2xl mx-auto ${
                        isDarkMode ? 'text-gray-300' : 'text-gray-600'
                      }`}>
                        我是您的專業碳管理顧問，基於最新的 2025 年 AI 技術，
                        精通 ISO 標準、碳足跡計算和減碳策略規劃。
                      </p>

                      {/* 2025年最新的智能建議卡片 */}
                      <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                        {intelligentSuggestions.map((suggestion, index) => (
                          <motion.button
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            onClick={() => handleSuggestionClick(suggestion.query)}
                            className={`group relative p-6 rounded-2xl text-left transition-all duration-300 hover:scale-105 transform ${
                              isDarkMode 
                                ? 'bg-gray-800/50 hover:bg-gray-800 border border-gray-700 hover:border-gray-600' 
                                : 'bg-white hover:bg-gray-50 border border-gray-200 hover:border-gray-300 shadow-lg hover:shadow-xl'
                            }`}
                          >
                            {/* 漸變背景 */}
                            <div className={`absolute inset-0 bg-gradient-to-br ${suggestion.color} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300`} />
                            
                            <div className="relative z-10">
                              <div className="flex items-start space-x-4">
                                <div className={`p-3 rounded-xl bg-gradient-to-br ${suggestion.color}`}>
                                  <suggestion.icon className="h-6 w-6 text-white" />
                                </div>
                                <div className="flex-1">
                                  <h3 className="font-semibold text-lg mb-2">{suggestion.title}</h3>
                                  <p className={`text-sm mb-3 ${
                                    isDarkMode ? 'text-gray-400' : 'text-gray-600'
                                  }`}>
                                    {suggestion.description}
                                  </p>
                                  <div className={`inline-flex items-center text-xs px-2 py-1 rounded-full ${
                                    isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                                  }`}>
                                    <Sparkles className="h-3 w-3 mr-1" />
                                    AI 專家模式
                                  </div>
                                </div>
                              </div>
                            </div>
                          </motion.button>
                        ))}
                      </div>
                    </motion.div>
                  ) : (
                    /* 對話消息 */
                    <>
                      {currentMessages.map((message) => (
                        <motion.div
                          key={message.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="flex items-start space-x-4 max-w-4xl mx-auto"
                        >
                          {/* 頭像 */}
                          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                            message.type === 'user'
                              ? isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                              : 'bg-gradient-to-br from-blue-500 to-purple-500'
                          }`}>
                            {message.type === 'user' ? (
                              <User className="h-5 w-5" />
                            ) : (
                              <Bot className="h-5 w-5 text-white" />
                            )}
                          </div>

                          {/* 消息內容 */}
                          <div className="flex-1 min-w-0">
                            <div className={`rounded-2xl p-4 ${
                              message.type === 'user'
                                ? isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200 shadow-sm'
                                : isDarkMode ? 'bg-gray-800/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'
                            }`}>
                              <div className="prose prose-sm max-w-none dark:prose-invert">
                                {message.type === 'assistant' ? (
                                  <div 
                                    dangerouslySetInnerHTML={{ 
                                      __html: message.content  // 直接使用content，因為已經是HTML格式了
                                    }}
                                    className="ai-response-content"
                                  />
                                ) : (
                                  message.content.split('\n').map((line, i) => (
                                    <p key={i} className="mb-2 last:mb-0">{line}</p>
                                  ))
                                )}
                              </div>
                              
                              {/* 引用來源 - RAG結果顯示 */}
                              {message.type === 'assistant' && message.sources && message.sources.length > 0 && (
                                <div className={`mt-4 pt-4 border-t ${
                                  isDarkMode ? 'border-gray-600' : 'border-gray-200'
                                }`}>
                                  <div className="flex items-center mb-3">
                                    <BookOpen className={`h-4 w-4 mr-2 ${
                                      isDarkMode ? 'text-emerald-400' : 'text-emerald-500'
                                    }`} />
                                    <span className={`text-sm font-medium ${
                                      isDarkMode ? 'text-gray-300' : 'text-gray-700'
                                    }`}>
                                      引用來源 ({message.sources.length})
                                    </span>
                                  </div>
                                  <div className="space-y-2">
                                    {message.sources.map((source, index) => (
                                      <div
                                        key={index}
                                        className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                                          isDarkMode 
                                            ? 'bg-gray-800/50 border-gray-600 hover:border-emerald-500' 
                                            : 'bg-gray-50 border-gray-200 hover:border-emerald-400'
                                        }`}
                                        onClick={() => {
                                          // 點擊查看文件詳情
                                          if (source.document_id) {
                                            const doc = documents.find(d => d.id === source.document_id);
                                            if (doc) setSelectedDocument(doc);
                                          }
                                        }}
                                      >
                                        <div className="flex items-start justify-between">
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center space-x-2 mb-1">
                                              <span className={`text-xs px-2 py-1 rounded font-medium ${
                                                isDarkMode 
                                                  ? 'bg-emerald-900 text-emerald-200' 
                                                  : 'bg-emerald-100 text-emerald-800'
                                              }`}>
                                                [{index + 1}]
                                              </span>
                                              <span className={`text-sm font-medium truncate ${
                                                isDarkMode ? 'text-gray-200' : 'text-gray-800'
                                              }`}>
                                                {source.title || source.filename || '未知文件'}
                                              </span>
                                            </div>
                                            <p className={`text-xs mb-2 ${
                                              isDarkMode ? 'text-gray-400' : 'text-gray-600'
                                            }`}>
                                              相關度: {((source.similarity || source.score || 0) * 100).toFixed(1)}%
                                            </p>
                                            <p className={`text-sm line-clamp-2 ${
                                              isDarkMode ? 'text-gray-300' : 'text-gray-700'
                                            }`}>
                                              {source.content || source.snippet || '無內容預覽'}
                                            </p>
                                          </div>
                                          <div className="flex-shrink-0 ml-3">
                                            <div className={`p-1.5 rounded ${
                                              isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                                            }`}>
                                              <FileText className={`h-3 w-3 ${
                                                isDarkMode ? 'text-gray-400' : 'text-gray-500'
                                              }`} />
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                  
                                  {/* RAG統計信息 */}
                                  {(message.context_used || message.search_query) && (
                                    <div className={`mt-3 pt-3 border-t text-xs ${
                                      isDarkMode 
                                        ? 'border-gray-600 text-gray-400' 
                                        : 'border-gray-200 text-gray-500'
                                    }`}>
                                      {message.context_used && (
                                        <span className="mr-4">
                                          📄 使用了 {message.context_used} 個上下文
                                        </span>
                                      )}
                                      {message.search_query && (
                                        <span>
                                          🔍 搜尋關鍵字: "{message.search_query}"
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )}
                              
                              {/* 消息操作 */}
                              <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200 dark:border-gray-600">
                                <span className={`text-xs ${
                                  isDarkMode ? 'text-gray-400' : 'text-gray-500'
                                }`}>
                                  {message.timestamp}
                                </span>
                                
                                {message.type === 'assistant' && (
                                  <div className="flex items-center space-x-2">
                                    <button
                                      onClick={() => copyToClipboard(message.content)}
                                      className={`p-1.5 rounded-lg transition-colors ${
                                        isDarkMode 
                                          ? 'hover:bg-gray-700 text-gray-400' 
                                          : 'hover:bg-gray-200 text-gray-500'
                                      }`}
                                      title="複製回答"
                                    >
                                      <Copy className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                      className={`p-1.5 rounded-lg transition-colors ${
                                        isDarkMode 
                                          ? 'hover:bg-gray-700 text-gray-400' 
                                          : 'hover:bg-gray-200 text-gray-500'
                                      }`}
                                      title="有幫助"
                                    >
                                      <ThumbsUp className="h-3.5 w-3.5" />
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}

                      {/* 載入動畫 */}
                      {isLoading && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="flex items-start space-x-4 max-w-4xl mx-auto"
                        >
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                            <Bot className="h-5 w-5 text-white" />
                          </div>
                          <div className={`rounded-2xl p-4 ${
                            isDarkMode ? 'bg-gray-800/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'
                          }`}>
                            <div className="flex items-center space-x-3">
                              <div className="flex space-x-1">
                                <div className={`w-2 h-2 rounded-full animate-bounce ${
                                  isDarkMode ? 'bg-gray-400' : 'bg-gray-500'
                                }`} />
                                <div className={`w-2 h-2 rounded-full animate-bounce delay-75 ${
                                  isDarkMode ? 'bg-gray-400' : 'bg-gray-500'
                                }`} />
                                <div className={`w-2 h-2 rounded-full animate-bounce delay-150 ${
                                  isDarkMode ? 'bg-gray-400' : 'bg-gray-500'
                                }`} />
                              </div>
                              <span className={`text-sm ${
                                isDarkMode ? 'text-gray-400' : 'text-gray-500'
                              }`}>
                                AI 正在思考中...
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      )}

                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                {/* 輸入區域 - 固定在底部 */}
                <div className={`border-t px-6 py-4 ${
                  isDarkMode 
                    ? 'border-gray-700 bg-gray-900' 
                    : 'border-gray-200 bg-white'
                }`}>
                  <div className="max-w-4xl mx-auto">
                    <div className="relative">
                      <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="輸入您的問題... (Enter 發送，Shift+Enter 換行)"
                        className={`w-full resize-none rounded-2xl border pr-14 pl-6 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${
                          isDarkMode 
                            ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-400' 
                            : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-500'
                        }`}
                        rows="1"
                        style={{ minHeight: '56px', maxHeight: '120px' }}
                      />
                      
                      <button
                        onClick={() => handleSendMessage()}
                        disabled={!inputValue.trim() || isLoading}
                        className={`absolute right-3 top-1/2 transform -translate-y-1/2 p-2 rounded-xl transition-all ${
                          inputValue.trim() && !isLoading
                            ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                            : isDarkMode 
                              ? 'bg-gray-700 text-gray-400' 
                              : 'bg-gray-200 text-gray-400'
                        }`}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </button>
                    </div>
                    
                    <p className={`text-xs text-center mt-3 ${
                      isDarkMode ? 'text-gray-500' : 'text-gray-400'
                    }`}>
                      AI 可能產生不準確資訊，請驗證重要內容 • 基於 Azure OpenAI 服務
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 知識庫管理標籤 */}
            {activeTab === 'knowledge' && (
              <div className="h-full overflow-y-auto">
                <div className="max-w-7xl mx-auto p-6">
                  {/* Header Section */}
                  <div className={`rounded-xl p-6 mb-6 ${
                    isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
                  }`}>
                    <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                      {/* Search */}
                      <div className="flex-1 max-w-md">
                        <div className="relative">
                          <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 ${
                            isDarkMode ? 'text-gray-400' : 'text-gray-500'
                          }`} />
                          <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="搜尋文件..."
                            className={`w-full pl-10 pr-4 py-3 rounded-lg border transition-colors ${
                              isDarkMode 
                                ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                                : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-500'
                            } focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent`}
                          />
                          {searchQuery && (
                            <button
                              onClick={() => setSearchQuery('')}
                              className={`absolute right-3 top-1/2 transform -translate-y-1/2 ${
                                isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'
                              }`}
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Filters and Actions */}
                      <div className="flex items-center gap-3">
                        {/* Sort */}
                        <select 
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value)}
                          className={`px-3 py-3 rounded-lg border ${
                            isDarkMode 
                              ? 'bg-gray-700 border-gray-600 text-white' 
                              : 'bg-white border-gray-300 text-gray-900'
                          } focus:outline-none focus:ring-2 focus:ring-emerald-500`}
                        >
                          <option value="newest">最新優先</option>
                          <option value="oldest">最舊優先</option>
                          <option value="title">標題排序</option>
                        </select>

                        {/* Upload Button */}
                        <div className="relative">
                          <input
                            type="file"
                            id="file-upload"
                            multiple
                            accept=".pdf,.doc,.docx,.txt,.md"
                            onChange={handleFileUpload}
                            className="hidden"
                          />
                          <label
                            htmlFor="file-upload"
                            className={`flex items-center space-x-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg cursor-pointer transition-colors ${
                              uploading ? 'opacity-50 cursor-not-allowed' : ''
                            }`}
                          >
                            <Upload className="h-4 w-4" />
                            <span>{uploading ? '上傳中...' : '上傳文件'}</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Drag & Drop Area */}
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`border-2 border-dashed rounded-xl p-8 mb-6 text-center transition-all ${
                      dragActive
                        ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                        : isDarkMode
                          ? 'border-gray-600 hover:border-gray-500'
                          : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <Upload className={`h-12 w-12 mx-auto mb-4 ${
                      dragActive 
                        ? 'text-emerald-500' 
                        : isDarkMode ? 'text-gray-400' : 'text-gray-500'
                    }`} />
                    <h3 className={`text-lg font-semibold mb-2 ${
                      dragActive 
                        ? 'text-emerald-600' 
                        : isDarkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}>
                      {dragActive ? '放開以上傳文件' : '拖拽文件到這裡上傳'}
                    </h3>
                    <p className={`text-sm ${
                      isDarkMode ? 'text-gray-400' : 'text-gray-500'
                    }`}>
                      支援 PDF, DOC, DOCX, TXT, MD 格式
                    </p>
                  </div>

                  {/* Document List Table */}
                  <div className={`rounded-xl border overflow-hidden ${
                    isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
                  }`}>
                    {/* Table Header */}
                    <div className={`grid grid-cols-12 gap-4 p-4 border-b font-medium text-sm ${
                      isDarkMode 
                        ? 'bg-gray-750 border-gray-700 text-gray-300' 
                        : 'bg-gray-50 border-gray-200 text-gray-600'
                    }`}>
                      <div className="col-span-6 flex items-center space-x-1">
                        <FileText className="h-4 w-4" />
                        <span>文件名稱</span>
                      </div>
                      <div className="col-span-3 flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>上傳日期</span>
                      </div>
                      <div className="col-span-2 flex items-center space-x-1">
                        <HardDrive className="h-4 w-4" />
                        <span>檔案大小</span>
                      </div>
                      <div className="col-span-1 text-center">操作</div>
                    </div>

                    {/* Table Body */}
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                      {filteredAndSortedDocuments.length === 0 ? (
                        <div className="p-8 text-center">
                          <FileText className={`h-12 w-12 mx-auto mb-4 ${
                            isDarkMode ? 'text-gray-400' : 'text-gray-400'
                          }`} />
                          <h3 className={`text-lg font-semibold mb-2 ${
                            isDarkMode ? 'text-gray-300' : 'text-gray-600'
                          }`}>
                            {searchQuery ? '找不到符合條件的文件' : '尚無文件'}
                          </h3>
                          <p className={`text-sm ${
                            isDarkMode ? 'text-gray-400' : 'text-gray-500'
                          }`}>
                            {searchQuery ? '請調整搜尋條件' : '上傳您的第一個文件來建立知識庫'}
                          </p>
                        </div>
                      ) : (
                        filteredAndSortedDocuments.map((doc, index) => (
                          <motion.div
                            key={doc.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.02 }}
                            className={`grid grid-cols-12 gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors cursor-pointer ${
                              isDarkMode ? 'text-gray-300' : 'text-gray-700'
                            }`}
                            onClick={() => openFilePreview(doc)}
                          >
                            {/* File Name */}
                            <div className="col-span-6 flex items-center space-x-3 min-w-0">
                              <div className={`p-2 rounded flex-shrink-0 ${
                                isDarkMode ? 'bg-emerald-600' : 'bg-emerald-100'
                              }`}>
                                <FileText className={`h-4 w-4 ${
                                  isDarkMode ? 'text-white' : 'text-emerald-600'
                                }`} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="font-medium truncate">{doc.title}</p>
                                <div className="flex items-center justify-between space-x-2">
                                  <p className={`text-xs truncate flex-1 ${
                                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                                  }`}>
                                    {doc.excerpt || '此文件沒有可預覽的內容'}
                                  </p>
                                  <span className={`text-xs px-2 py-1 rounded-full ${
                                    isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                                  }`}>
                                    {doc.original_name?.split('.').pop()?.toUpperCase() || 'FILE'}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Date */}
                            <div className={`col-span-3 flex items-center text-sm ${
                              isDarkMode ? 'text-gray-400' : 'text-gray-600'
                            }`}>
                              {doc.created_at ? new Date(doc.created_at).toLocaleDateString('zh-TW') : '--'}
                            </div>

                            {/* Size */}
                            <div className={`col-span-2 flex items-center text-sm ${
                              isDarkMode ? 'text-gray-400' : 'text-gray-600'
                            }`}>
                              {doc.size ? `${(doc.size / 1024).toFixed(1)} KB` : '--'}
                            </div>

                            {/* Actions */}
                            <div className="col-span-1 flex items-center justify-center space-x-1">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  openFilePreview(doc)
                                }}
                                className={`p-1.5 rounded transition-colors ${
                                  isDarkMode 
                                    ? 'hover:bg-gray-700 text-gray-400' 
                                    : 'hover:bg-gray-100 text-gray-500'
                                }`}
                                title="預覽文件"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setDeleteConfirm(doc)
                                }}
                                className={`p-1.5 rounded transition-colors ${
                                  isDarkMode 
                                    ? 'hover:bg-red-700 text-red-400' 
                                    : 'hover:bg-red-100 text-red-500'
                                }`}
                                title="刪除文件"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Search Results */}
                  {searchResults.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-lg font-medium mb-4">搜尋結果 ({searchResults.length})</h3>
                      <div className="space-y-3">
                        {searchResults.map((result, index) => (
                          <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className={`rounded-lg p-4 border transition-colors cursor-pointer ${
                              isDarkMode 
                                ? 'bg-gray-800 border-gray-700 hover:bg-gray-750' 
                                : 'bg-white border-gray-200 hover:bg-gray-50'
                            }`}
                            onClick={() => openFilePreview(result)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <h4 className="font-medium mb-1">{result.title}</h4>
                                <p className={`text-sm mb-2 ${
                                  isDarkMode ? 'text-gray-300' : 'text-gray-600'
                                }`}>
                                  {result.excerpt}
                                </p>
                                <div className="flex items-center space-x-2">
                                  <span className={`text-xs ${
                                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                                  }`}>
                                    相關度: {Math.round((result.similarity || result.score || 0) * 100)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Document Detail Modal */}
        {selectedDocument && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className={`w-full max-w-4xl mx-4 max-h-[80vh] overflow-y-auto rounded-xl p-6 ${
              isDarkMode ? 'bg-gray-800' : 'bg-white'
            }`}>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-semibold">{selectedDocument.title || selectedDocument.filename}</h3>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      isDarkMode ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {selectedDocument.category || '一般文件'}
                    </span>
                    {selectedDocument.created_at && (
                      <span className={`text-sm ${
                        isDarkMode ? 'text-gray-400' : 'text-gray-500'
                      }`}>
                        {new Date(selectedDocument.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedDocument(null)}
                  className={`p-2 rounded-lg transition-colors ${
                    isDarkMode 
                      ? 'hover:bg-gray-700 text-gray-300' 
                      : 'hover:bg-gray-100 text-gray-600'
                  }`}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              
              <div className={`prose max-w-none ${
                isDarkMode ? 'prose-invert' : ''
              }`}>
                {selectedDocument.content && selectedDocument.content.split('\n').map((paragraph, index) => (
                  <p key={index} className="mb-4">{paragraph}</p>
                ))}
                {!selectedDocument.content && (
                  <p className={`text-center py-8 ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    文件內容無法預覽
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className={`w-full max-w-md mx-4 rounded-xl p-6 ${
              isDarkMode ? 'bg-gray-800' : 'bg-white'
            }`}>
              <h3 className="text-lg font-semibold mb-4">確認刪除</h3>
              <p className={`mb-6 ${
                isDarkMode ? 'text-gray-300' : 'text-gray-600'
              }`}>
                確定要刪除文件「{deleteConfirm.title || deleteConfirm.filename}」嗎？此操作無法復原。
              </p>
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    isDarkMode 
                      ? 'bg-gray-700 hover:bg-gray-600 text-gray-300' 
                      : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                  }`}
                >
                  取消
                </button>
                <button
                  onClick={() => handleDeleteDocument(deleteConfirm.id)}
                  className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                >
                  確認刪除
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Notification */}
        {notification && (
          <div className={`fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            notification.type === 'success' 
              ? 'bg-green-500 text-white' 
              : notification.type === 'error'
              ? 'bg-red-500 text-white'
              : 'bg-blue-500 text-white'
          }`}>
            {notification.message}
          </div>
        )}

        {/* File Preview Modal */}
        {previewMode && previewDocument && (
          <div className={`fixed inset-0 z-50 ${isFullscreen ? '' : 'p-4'}`}>
            <div className="absolute inset-0 bg-black bg-opacity-50" onClick={closePreview} />
            <div className={`relative bg-white dark:bg-gray-800 rounded-lg shadow-2xl flex flex-col ${
              isFullscreen ? 'h-full' : 'h-full max-h-[90vh]'
            } ${isFullscreen ? '' : 'max-w-6xl mx-auto'}`}>
              {/* Preview Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-emerald-100 dark:bg-emerald-600 rounded">
                    <FileText className="h-5 w-5 text-emerald-600 dark:text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">{previewDocument.title}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {previewDocument.original_name} • 
                      {previewDocument.size ? ` ${(previewDocument.size / 1024).toFixed(1)} KB` : ' 未知大小'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={toggleFullscreen}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    title={isFullscreen ? '退出全屏' : '全屏顯示'}
                  >
                    {isFullscreen ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronUp className="h-5 w-5" />
                    )}
                  </button>
                  <button
                    onClick={closePreview}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Preview Content */}
              <div className="flex-1 overflow-auto">
                {previewLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                    <span className="ml-3 text-gray-600 dark:text-gray-400">載入中...</span>
                  </div>
                ) : (
                  <div className="h-full">
                    {isPdfFile(previewDocument?.title) ? (
                      /* PDF預覽器 */
                      <SimplePdfViewer
                        pdfUrl={getFileUrl(previewDocument.id)}
                        fileName={previewDocument.title}
                        isDarkMode={isDarkMode}
                        zoomLevel={zoomLevel}
                        onZoomChange={setZoomLevel}
                        onDownload={downloadFile}
                        onPrint={printFile}
                        onFullscreen={toggleFullscreen}
                      />
                    ) : (
                      /* 文字內容預覽 */
                      <div className="p-6">
                        {previewDocument.content ? (
                          <div className="prose max-w-none dark:prose-invert">
                            {previewDocument.content.split('\n').map((paragraph, index) => (
                              <p key={index} className="mb-4 leading-relaxed">
                                {paragraph}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-12">
                            <FileText className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                            <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                              無法預覽此文件
                            </h3>
                            <p className="text-gray-500 dark:text-gray-500">
                              此文件類型不支援預覽，或者文件內容無法載入
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Preview Footer */}
              <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    上傳時間: {previewDocument.created_at ? 
                      new Date(previewDocument.created_at).toLocaleString('zh-TW') : '未知'}
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => copyToClipboard(previewDocument.content || '')}
                      className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                    >
                      複製內容
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Ultra2025KnowledgeBase
