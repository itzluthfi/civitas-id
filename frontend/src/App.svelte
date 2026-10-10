<script lang="ts">
  import { onMount } from 'svelte'
  import {
    Search,
    FileText,
    Download,
    ExternalLink,
    GraduationCap,
    Building2,
    BookOpen,
    CheckCircle2,
    Loader2,
    CreditCard,
    FileSpreadsheet,
    Globe,
    Filter,
    ArrowUpDown,
    History,
    Copy,
    Check,
    Eye,
    Archive,
    X,
    RotateCcw,
    ChevronLeft,
    ChevronRight,
    Maximize2,
    HelpCircle,
    Info,
    Shield,
    Server,
    Code2,
    Users,
    BarChart3,
    Phone,
    Mail,
    MapPin,
    Award,
    Trash2,
    ChevronRight as ArrowRight,
    Sun,
    Moon,
    Upload,
    Camera,
    Compass,
    User,
    ChevronDown
  } from '@lucide/svelte'
  import SearchableSelect from './lib/components/SearchableSelect.svelte'
  import ApiDocs from './lib/components/ApiDocs.svelte'
  import {
    searchMahasiswa,
    getDetailMahasiswa,
    searchDosen,
    getDetailDosen,
    searchPT,
    getDetailPT,
    previewDocument,
    downloadDocument
  } from './lib/api'
  import type {
    MahasiswaSummary,
    MahasiswaDetail,
    DosenSummary,
    DosenDetail,
    PTSummary,
    PTDetail
  } from './lib/types'

  // Main View Navigation ('explorer' | 'docs')
  let activeView = $state<'explorer' | 'docs'>('explorer')

  // Search Category ('mhs' | 'dosen' | 'pt')
  let searchCategory = $state<'mhs' | 'dosen' | 'pt'>('mhs')

  // Search Input & Query State
  let searchQuery = $state('')
  let isSearching = $state(false)
  let searchError = $state<string | null>(null)
  let recentSearches = $state<string[]>([])

  // Category Results
  let resultsMhs = $state<MahasiswaSummary[]>([])
  let resultsDosen = $state<DosenSummary[]>([])
  let resultsPT = $state<PTSummary[]>([])

  // Selected State
  let selectedId = $state<string | null>(null)
  let mhsDetail = $state<MahasiswaDetail | null>(null)
  let dosenDetail = $state<DosenDetail | null>(null)
  let ptDetail = $state<PTDetail | null>(null)
  let isLoadingDetail = $state(false)

  // Filtering State
  let filterKampus = $state<string>('')
  let filterProdi = $state<string>('')
  let localKeyword = $state<string>('')
  let sortBy = $state<'default' | 'name-asc' | 'name-desc' | 'code-asc' | 'code-desc'>('default')

  // Pagination State
  let currentPage = $state(1)
  let pageSize = $state(8)

  // Mobile View Mode ('list' | 'detail')
  let mobileTab = $state<'list' | 'detail'>('list')

  // Document & Preview State (For Mahasiswa)
  let activeTemplate = $state<'skma_bilingual' | 'skma_id' | 'ktm' | 'transcript'>('skma_bilingual')
  let isDownloading = $state<string | null>(null)
  let isBatchDownloading = $state(false)
  let inlinePreviewUrl = $state<string | null>(null)
  let isGeneratingInlinePreview = $state(false)
  let showFullscreenModal = $state(false)

  // Theme State: 'light' is default
  let theme = $state<'light' | 'dark'>('light')

  function applyTheme(t: 'light' | 'dark') {
    theme = t
    localStorage.setItem('civitas_theme', t)
    if (t === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleTheme() {
    applyTheme(theme === 'light' ? 'dark' : 'light')
  }

  // About & FAQ Modal State
  let showAboutModal = $state(false)
  let activeFaqIndex = $state<number | null>(0)

  // Clipboard copy feedback
  let copiedField = $state<string | null>(null)

  // Custom Student Photo State (for KTM and Document Rendering)
  let customStudentPhoto = $state<string | null>(null)

  function handlePhotoUpload(event: Event) {
    const input = event.target as HTMLInputElement
    if (input.files && input.files[0]) {
      const file = input.files[0]
      if (file.size > 5 * 1024 * 1024) {
        alert('Ukuran foto maksimal 5 MB.')
        return
      }
      const reader = new FileReader()
      reader.onload = (e) => {
        customStudentPhoto = e.target?.result as string
        if (mhsDetail) {
          mhsDetail.photo_base64 = customStudentPhoto
          loadInlinePreview()
        }
      }
      reader.readAsDataURL(file)
    }
  }

  function removeStudentPhoto() {
    customStudentPhoto = null
    if (mhsDetail) {
      delete mhsDetail.photo_base64
      loadInlinePreview()
    }
  }

  function resolveLeaderTitle(ptName?: string): string {
    if (!ptName) return 'Pimpinan Perguruan Tinggi'
    const n = ptName.toLowerCase()
    if (n.includes('universitas')) return 'Rektor Universitas'
    if (n.includes('institut')) return 'Rektor Institut'
    if (n.includes('politeknik')) return 'Direktur Politeknik'
    if (n.includes('akademi')) return 'Direktur Akademi'
    if (n.includes('sekolah tinggi')) return 'Ketua Sekolah Tinggi'
    return 'Pimpinan Perguruan Tinggi'
  }

  // Program Studi Table Filtering & Pagination
  let prodiSearch = $state('')
  let prodiPage = $state(1)
  let prodiPageSize = $state(5)

  let filteredProdiList = $derived.by(() => {
    const list = ptDetail?.prodi_list || []
    if (!prodiSearch.trim()) return list
    const q = prodiSearch.toLowerCase().trim()
    return list.filter(p =>
      (p.nama_prodi && p.nama_prodi.toLowerCase().includes(q)) ||
      (p.kode_prodi && p.kode_prodi.toLowerCase().includes(q)) ||
      (p.jenjang_prodi && p.jenjang_prodi.toLowerCase().includes(q)) ||
      (p.akreditasi && p.akreditasi.toLowerCase().includes(q))
    )
  })

  let prodiTotalPages = $derived(Math.max(1, Math.ceil(filteredProdiList.length / prodiPageSize)))
  let paginatedProdiList = $derived.by(() => {
    const start = (prodiPage - 1) * prodiPageSize
    return filteredProdiList.slice(start, start + prodiPageSize)
  })

  function formatIndoDate(dateStr?: string): string {
    if (!dateStr) return '-'
    try {
      const d = new Date(dateStr)
      if (isNaN(d.getTime())) return dateStr
      const months = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
      ]
      return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
    } catch {
      return dateStr
    }
  }

  function formatSemesterName(sem?: string): string {
    if (!sem) return 'Terbaru'
    const str = String(sem)
    if (str.length === 5) {
      const year = str.slice(0, 4)
      const term = str.slice(4)
      if (term === '1') return `Ganjil ${year}`
      if (term === '2') return `Genap ${year}`
      if (term === '3') return `Pendek ${year}`
    }
    return sem
  }

  // Category presets
  const CATEGORY_PRESETS: Record<'mhs' | 'dosen' | 'pt', { label: string; query: string }[]> = {
    mhs: [
      { label: 'Telkom Univ', query: '1203230028' },
      { label: 'Univ Indonesia', query: 'Universitas Indonesia' },
      { label: 'ITB Bandung', query: 'Institut Teknologi Bandung' },
      { label: 'UGM Yogya', query: 'Universitas Gadjah Mada' }
    ],
    dosen: [
      { label: 'Prof. Bambang', query: 'Bambang' },
      { label: 'Dr. Hendra', query: 'Hendra' },
      { label: 'Siti Aminah', query: 'Siti Aminah' }
    ],
    pt: [
      { label: 'Univ Indonesia', query: 'Universitas Indonesia' },
      { label: 'ITB Bandung', query: 'Institut Teknologi Bandung' },
      { label: 'UGM Yogyakarta', query: 'Universitas Gadjah Mada' },
      { label: 'Telkom Univ', query: 'Telkom' }
    ]
  }

  // Placeholder texts per category
  let searchPlaceholder = $derived.by(() => {
    if (searchCategory === 'mhs') return 'Cari Mahasiswa: Masukkan NIM atau Nama (misal: 1203230028, Rizky Pratama)...'
    if (searchCategory === 'dosen') return 'Cari Dosen: Masukkan NIDN, NUPTK, atau Nama Dosen (misal: Bambang Hermanto, Siti Aminah)...'
    return 'Cari Perguruan Tinggi: Masukkan Nama Kampus atau Kode PT (misal: Universitas Indonesia, ITB, 001002)...'
  })

  // FAQ Items (Strict anti-slop, clear factual explanations)
  const FAQ_ITEMS = [
    {
      q: 'Apa itu CivitasID dan apa tujuannya?',
      a: 'CivitasID adalah platform utilitas kecerdasan data akademik terbuka (open academic intelligence) dan generator dokumen digital independen. CivitasID mengintegrasikan pangkalan data pendidikan tinggi Kemdiktisaintek RI dengan sumber-sumber ilmiah publik untuk mempermudah verifikasi keaktifan akademik, penelusuran rekam jejak riset, dan pembuatan berkas administratif standar seperti SKMA Bilingual, SKMA Standar Indonesia, KTM Digital CR80, dan Transkrip Sementara.'
    },
    {
      q: 'Sumber data apa saja yang digunakan oleh CivitasID?',
      a: 'CivitasID menggabungkan 7 ekosistem data publik resmi: 1) PDDIKTI Kemdiktisaintek (data induk mahasiswa, dosen, kampus, dan kurikulum), 2) SINTA Kemdiktisaintek (profil riset dosen, foto author, SINTA Score, dan Scopus H-Index), 3) Google Scholar (indeks sitasi dan karya ilmiah internasional), 4) Wikipedia Indonesia & Wikidata (nama pimpinan statuta, jenis institusi, dan sejarah), 5) Situs Web Resmi Kampus (saluran media sosial resmi dan email institusi), 6) RAMA Kemdiktisaintek (repositori nasional skripsi dan tugas akhir mahasiswa), dan 7) SIVIL Kemdiktisaintek (sistem verifikasi ijazah elektronik nasional).'
    },
    {
      q: 'Data apa saja yang diambil dan ditampilkan untuk setiap entitas?',
      a: '• Mahasiswa: Nama, NIM, Jenjang, Program Studi, Status Keaktifan (Aktif/Lulus/Cuti), Tanggal Masuk, Jenis Kelamin, tautan verifikasi PDDIKTI, penelusuran naskah skripsi di RAMA, verifikasi ijazah di SIVIL, dan fitur unggah pas foto formal beresolusi tinggi untuk dokumen digital.\n• Dosen: Nama Lengkap & Gelar, NIDN/NUPTK, Homebase PT & Prodi, Jabatan Akademik, Status Keaktifan, Riwayat Pendidikan Tinggi, Riwayat Aktivitas Mengajar per semester, Pas Foto Asli Author, SINTA ID & Score (3Yr/Overall), Scopus H-Index, dan Google Scholar H-Index.\n• Perguruan Tinggi: Kode PT, Nama Resmi, Akreditasi Institusi, Rentang Biaya Kuliah (SPP), Tanggal & No SK Pendirian, Kontak Resmi (Email, Telp, Fax, Web), Alamat Lengkap & Kode Pos, Nama Rektor / Direktur / Pimpinan resmi dari dokumen statuta, Media Sosial Resmi Kampus (Instagram, YouTube, LinkedIn, X/Twitter), Koordinat Satelit GPS + Buka di Google Maps, Rasio Dosen : Mahasiswa, Rata-rata Masa Studi per jenjang, Tabel Program Studi Lengkap (dapat dicari & difilter), Sarana Prasarana (Sarpras), serta Riwayat Perubahan Kampus.'
    },
    {
      q: 'Mengapa nomor telepon dan email pribadi mahasiswa tidak ditampilkan?',
      a: 'Sesuai UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP), nomor telepon seluler dan email pribadi mahasiswa tergolong sebagai data pribadi yang tidak dipublikasikan secara terbuka oleh PDDIKTI maupun CivitasID guna mencegah risiko penipuan, pinjol ilegal, dan kebocoran kontak pribadi.'
    },
    {
      q: 'Bagaimana foto dosen dan foto mahasiswa diperoleh?',
      a: '• Dosen: Foto profil dosen disinkronkan secara otomatis dari foto author yang terindeks secara publik pada pangkalan data SINTA Kemdiktisaintek atau profil Google Scholar resmi dosen bersangkutan.\n• Mahasiswa: PDDIKTI tidak merilis foto mahasiswa ke publik demi mematuhi UU PDP. Namun, CivitasID menyediakan fitur Pas Foto Uploader di browser pengguna, sehingga mahasiswa dapat menyematkan pas foto formal mereka secara lokal ke dalam KTM Digital dan SKMA tanpa data foto dikirim atau disimpan permanen ke server.'
    },
    {
      q: 'Bagaimana nama rektor atau pimpinan kampus bisa terdata?',
      a: 'CivitasID melakukan cross-referencing otomatis antara profil perguruan tinggi di PDDIKTI dengan infobox ensiklopedia Wikipedia Bahasa Indonesia dan basis data Wikidata yang bersumber dari dokumen statuta pendirian perguruan tinggi serta direktori pimpinan LLDIKTI Kemdiktisaintek RI.'
    },
    {
      q: 'Bagaimana kop surat, nama dekan, dan stempel dibuat secara dinamis?',
      a: 'Sistem membaca data perguruan tinggi dari profil PDDIKTI yang dicari. Mesin perender dinamis (university_resolver) memetakan akronim kampus, fakultas yang menaungi program studi, dan kota domisili kampus secara otomatis. Stempel kurva vektor SVG (<textPath>) dan lambang heraldik resmi kampus dirangkai secara prosedural tanpa template hardcoded satu kampus.'
    },
    {
      q: 'Apakah CivitasID menyimpan data pribadi di database server?',
      a: 'Tidak (Zero-Storage Policy). CivitasID tidak menyimpan data pribadi, NIM, nama mahasiswa, maupun dokumen unduhan ke dalam basis data permanen. Seluruh data hanya diproses secara transitif dalam memori server untuk render dokumen PDF/PNG dan disimpan sementara di cache memori (TTL 24 jam) guna efisiensi bandwidth upstream.'
    },
    {
      q: 'Apakah dokumen yang dihasilkan memiliki validitas verifikasi?',
      a: 'Setiap berkas dokumen yang dihasilkan dilengkapi QR Code verifikasi resmi yang langsung mengarah ke halaman profil mahasiswa pada situs resmi PDDIKTI Kemdiktisaintek RI. Siapa pun dapat memindai QR Code tersebut untuk memverifikasi keabsahan nomor registrasi dan status keaktifan mahasiswa di pangkalan data nasional.'
    },
    {
      q: 'Bagaimana cara menggunakan layanan Bot Telegram bawaan?',
      a: 'Modul bot Telegram telah terintegrasi di backend (app/bot/telegram_service.py berbasis aiogram 3). Anda cukup mengisi TELEGRAM_BOT_TOKEN dan ENABLE_TELEGRAM_BOT=true pada file .env backend. Bot akan aktif merespons perintah /cari [NIM atau Nama] dan mengirimkan dokumen PDF langsung ke ruang obrolan Telegram.'
    },
    {
      q: 'Apakah proyek ini Open Source?',
      a: 'Ya. CivitasID dilisensikan di bawah lisensi terbuka MIT. Kode sumber backend (Python/FastAPI/Playwright) dan frontend (Svelte 5/Vite/Tailwind v4) bebas diaudit, dikloning, dan dikembangkan untuk keperluan riset maupun kebutuhan sivitas akademika di Indonesia.'
    }
  ]

  // Derived: Unique University List for SearchableSelect
  let kampusOptions = $derived.by(() => {
    const map = new Map<string, number>()
    if (searchCategory === 'mhs') {
      resultsMhs.forEach(r => {
        const k = r.sinkatan_pt || r.nama_pt
        map.set(k, (map.get(k) || 0) + 1)
      })
    } else if (searchCategory === 'dosen') {
      resultsDosen.forEach(r => {
        const k = r.sinkatan_pt || r.nama_pt
        map.set(k, (map.get(k) || 0) + 1)
      })
    }
    return Array.from(map.entries())
      .map(([k, count]) => ({ value: k, label: k, count }))
      .sort((a, b) => a.label.localeCompare(b.label))
  })

  // Derived: Unique Study Program List for SearchableSelect
  let prodiOptions = $derived.by(() => {
    const map = new Map<string, number>()
    if (searchCategory === 'mhs') {
      resultsMhs.forEach(r => {
        map.set(r.nama_prodi, (map.get(r.nama_prodi) || 0) + 1)
      })
    } else if (searchCategory === 'dosen') {
      resultsDosen.forEach(r => {
        map.set(r.nama_prodi, (map.get(r.nama_prodi) || 0) + 1)
      })
    }
    return Array.from(map.entries())
      .map(([p, count]) => ({ value: p, label: p, count }))
      .sort((a, b) => a.label.localeCompare(b.label))
  })

  // Derived: Filtered & Sorted Search Results
  let filteredResults = $derived.by(() => {
    const kw = localKeyword.trim().toLowerCase()

    if (searchCategory === 'mhs') {
      let list = resultsMhs.filter(item => {
        const k = item.sinkatan_pt || item.nama_pt
        const matchKampus = !filterKampus || k === filterKampus
        const matchProdi = !filterProdi || item.nama_prodi === filterProdi
        const matchKw = !kw ||
          item.nama.toLowerCase().includes(kw) ||
          item.nim.includes(kw) ||
          item.nama_prodi.toLowerCase().includes(kw) ||
          k.toLowerCase().includes(kw)
        return matchKampus && matchProdi && matchKw
      })
      if (sortBy === 'name-asc') list.sort((a, b) => a.nama.localeCompare(b.nama))
      else if (sortBy === 'name-desc') list.sort((a, b) => b.nama.localeCompare(a.nama))
      else if (sortBy === 'code-asc') list.sort((a, b) => a.nim.localeCompare(b.nim))
      else if (sortBy === 'code-desc') list.sort((a, b) => b.nim.localeCompare(a.nim))
      return list
    }

    if (searchCategory === 'dosen') {
      let list = resultsDosen.filter(item => {
        const k = item.sinkatan_pt || item.nama_pt
        const matchKampus = !filterKampus || k === filterKampus
        const matchProdi = !filterProdi || item.nama_prodi === filterProdi
        const matchKw = !kw ||
          item.nama.toLowerCase().includes(kw) ||
          item.nidn.includes(kw) ||
          item.nama_prodi.toLowerCase().includes(kw) ||
          k.toLowerCase().includes(kw)
        return matchKampus && matchProdi && matchKw
      })
      if (sortBy === 'name-asc') list.sort((a, b) => a.nama.localeCompare(b.nama))
      else if (sortBy === 'name-desc') list.sort((a, b) => b.nama.localeCompare(a.nama))
      else if (sortBy === 'code-asc') list.sort((a, b) => a.nidn.localeCompare(b.nidn))
      else if (sortBy === 'code-desc') list.sort((a, b) => b.nidn.localeCompare(a.nidn))
      return list
    }

    if (searchCategory === 'pt') {
      let list = resultsPT.filter(item => {
        const matchKw = !kw ||
          item.nama.toLowerCase().includes(kw) ||
          item.kode.toLowerCase().includes(kw) ||
          (item.nama_singkat && item.nama_singkat.toLowerCase().includes(kw))
        return matchKw
      })
      if (sortBy === 'name-asc') list.sort((a, b) => a.nama.localeCompare(b.nama))
      else if (sortBy === 'name-desc') list.sort((a, b) => b.nama.localeCompare(a.nama))
      else if (sortBy === 'code-asc') list.sort((a, b) => a.kode.localeCompare(b.kode))
      else if (sortBy === 'code-desc') list.sort((a, b) => b.kode.localeCompare(a.kode))
      return list
    }

    return []
  })

  // Total results across current category
  let totalRawResults = $derived.by(() => {
    if (searchCategory === 'mhs') return resultsMhs.length
    if (searchCategory === 'dosen') return resultsDosen.length
    return resultsPT.length
  })

  // Pagination Calculations
  let totalPages = $derived(Math.max(1, Math.ceil(filteredResults.length / pageSize)))
  let paginatedResults = $derived.by(() => {
    const start = (currentPage - 1) * pageSize
    return filteredResults.slice(start, start + pageSize)
  })

  $effect(() => {
    filterKampus; filterProdi; localKeyword; sortBy; pageSize; searchCategory;
    currentPage = 1
  })

  let isAnyFilterActive = $derived(!!filterKampus || !!filterProdi || !!localKeyword.trim() || sortBy !== 'default')

  function resetFilters() {
    filterKampus = ''
    filterProdi = ''
    localKeyword = ''
    sortBy = 'default'
    currentPage = 1
  }

  function handleCategorySwitch(cat: 'mhs' | 'dosen' | 'pt') {
    if (searchCategory === cat) return
    searchCategory = cat
    searchError = null
    selectedId = null
    mhsDetail = null
    dosenDetail = null
    ptDetail = null
    inlinePreviewUrl = null
    resetFilters()
  }

  function addRecentSearch(q: string) {
    const clean = q.trim()
    if (!clean) return
    const updated = [clean, ...recentSearches.filter(s => s.toLowerCase() !== clean.toLowerCase())].slice(0, 6)
    recentSearches = updated
    try {
      localStorage.setItem('civitas_recent_searches', JSON.stringify(updated))
    } catch {}
  }

  function removeRecentSearch(q: string, e: Event) {
    e.stopPropagation()
    recentSearches = recentSearches.filter(s => s !== q)
    try {
      localStorage.setItem('civitas_recent_searches', JSON.stringify(recentSearches))
    } catch {}
  }

  function clearAllRecentSearches() {
    recentSearches = []
    try {
      localStorage.removeItem('civitas_recent_searches')
    } catch {}
  }

  async function handleSearch(queryToUse?: string) {
    const q = queryToUse !== undefined ? queryToUse : searchQuery
    if (!q.trim() || q.trim().length < 2) return

    searchQuery = q.trim()
    isSearching = true
    searchError = null
    selectedId = null
    mhsDetail = null
    dosenDetail = null
    ptDetail = null
    inlinePreviewUrl = null
    resetFilters()
    addRecentSearch(q)
    mobileTab = 'list'

    try {
      if (searchCategory === 'mhs') {
        resultsMhs = await searchMahasiswa(q.trim())
        if (resultsMhs.length === 0) {
          searchError = 'Data mahasiswa tidak ditemukan di basis data PDDIKTI.'
        } else if (resultsMhs.length === 1) {
          selectItem(resultsMhs[0].id)
        }
      } else if (searchCategory === 'dosen') {
        resultsDosen = await searchDosen(q.trim())
        if (resultsDosen.length === 0) {
          searchError = 'Data dosen tidak ditemukan di basis data PDDIKTI.'
        } else if (resultsDosen.length === 1) {
          selectItem(resultsDosen[0].id)
        }
      } else if (searchCategory === 'pt') {
        resultsPT = await searchPT(q.trim())
        if (resultsPT.length === 0) {
          searchError = 'Data perguruan tinggi tidak ditemukan di basis data PDDIKTI.'
        } else if (resultsPT.length === 1) {
          selectItem(resultsPT[0].id)
        }
      }
    } catch (err: any) {
      searchError = err.message || 'Gagal menghubungi server PDDIKTI.'
    } finally {
      isSearching = false
    }
  }

  async function selectItem(id: string) {
    selectedId = id
    isLoadingDetail = true
    inlinePreviewUrl = null
    mobileTab = 'detail'
    prodiSearch = ''
    prodiPage = 1
    customStudentPhoto = null

    try {
      if (searchCategory === 'mhs') {
        mhsDetail = await getDetailMahasiswa(id)
        loadInlinePreview()
      } else if (searchCategory === 'dosen') {
        dosenDetail = await getDetailDosen(id)
      } else if (searchCategory === 'pt') {
        ptDetail = await getDetailPT(id)
      }
    } catch (err: any) {
      searchError = 'Gagal memuat rincian data dari PDDIKTI.'
    } finally {
      isLoadingDetail = false
    }
  }

  async function loadInlinePreview() {
    if (!mhsDetail) return
    isGeneratingInlinePreview = true
    try {
      if (inlinePreviewUrl) window.URL.revokeObjectURL(inlinePreviewUrl)
      inlinePreviewUrl = await previewDocument(activeTemplate, mhsDetail)
    } catch (err: any) {
      console.error('Preview error:', err)
    } finally {
      isGeneratingInlinePreview = false
    }
  }

  function onTemplateChange(t: 'skma_bilingual' | 'skma_id' | 'ktm' | 'transcript') {
    activeTemplate = t
    loadInlinePreview()
  }

  async function handleDownload(format: 'pdf' | 'png') {
    if (!mhsDetail) return
    isDownloading = `${activeTemplate}-${format}`
    try {
      await downloadDocument(activeTemplate, format, mhsDetail)
    } catch (err: any) {
      alert(`Gagal mengunduh dokumen: ${err.message}`)
    } finally {
      isDownloading = null
    }
  }

  async function handleBatchDownload() {
    if (!mhsDetail) return
    isBatchDownloading = true
    const templates: ('skma_bilingual' | 'skma_id' | 'ktm' | 'transcript')[] = [
      'skma_bilingual',
      'skma_id',
      'ktm',
      'transcript'
    ]
    try {
      for (const t of templates) {
        await downloadDocument(t, 'pdf', mhsDetail)
      }
    } catch (err: any) {
      alert(`Gagal mengunduh paket lengkap: ${err.message}`)
    } finally {
      isBatchDownloading = false
    }
  }

  function copyToClipboard(text: string, fieldName: string) {
    navigator.clipboard.writeText(text)
    copiedField = fieldName
    setTimeout(() => {
      if (copiedField === fieldName) copiedField = null
    }, 2000)
  }

  onMount(() => {
    try {
      const stored = localStorage.getItem('civitas_recent_searches')
      if (stored) recentSearches = JSON.parse(stored)
    } catch {}

    const savedTheme = (localStorage.getItem('civitas_theme') as 'light' | 'dark') || 'light'
    applyTheme(savedTheme)
  })
</script>

<div class="min-h-screen bg-slate-50 dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 flex flex-col selection:bg-sky-500/30 selection:text-sky-900 dark:selection:bg-sky-900 dark:selection:text-white antialiased transition-colors duration-150">
  <!-- Top Navigation Header -->
  <header class="border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-sky-600 border border-sky-400 flex items-center justify-center text-white font-bold text-sm tracking-wider shadow-sm">
          CID
        </div>
        <div class="flex items-center space-x-2">
          <span class="font-bold text-slate-900 dark:text-white tracking-tight text-base">CivitasID</span>
        </div>
      </div>

      <!-- Center Navigation View Tabs (Desktop) -->
      <nav class="hidden md:flex items-center space-x-1 bg-slate-100 dark:bg-[#131b2e] p-1 rounded-xl border border-slate-200 dark:border-slate-700/80">
        <button
          type="button"
          onclick={() => activeView = 'explorer'}
          class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer flex items-center gap-1.5 {activeView === 'explorer' ? 'bg-sky-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'}"
        >
          <Search size={14} />
          <span>Eksplorasi Data</span>
        </button>
        <button
          type="button"
          onclick={() => activeView = 'docs'}
          class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer flex items-center gap-1.5 {activeView === 'docs' ? 'bg-sky-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'}"
        >
          <BookOpen size={14} />
          <span>Dokumentasi API</span>
        </button>
      </nav>

      <div class="flex items-center space-x-2 text-xs text-slate-700 dark:text-slate-300">
        <!-- Theme Toggle (Light Default / Dark) -->
        <button
          type="button"
          onclick={toggleTheme}
          class="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 hover:border-slate-400 dark:hover:border-slate-500 text-slate-700 dark:text-slate-200 transition font-semibold flex items-center gap-1.5 cursor-pointer shadow-2xs"
          title={theme === 'light' ? 'Beralih ke Tema Gelap' : 'Beralih ke Tema Terang'}
        >
          {#if theme === 'light'}
            <Sun size={14} class="text-amber-500" />
            <span class="hidden sm:inline">Terang</span>
          {:else}
            <Moon size={14} class="text-sky-400" />
            <span class="hidden sm:inline">Gelap</span>
          {/if}
        </button>

        <!-- Mobile Docs Switcher Pill -->
        <button
          type="button"
          onclick={() => activeView = activeView === 'explorer' ? 'docs' : 'explorer'}
          class="md:hidden px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-[#1e293b] text-sky-700 dark:text-sky-300 font-bold flex items-center gap-1 cursor-pointer"
        >
          {#if activeView === 'explorer'}
            <BookOpen size={13} />
            <span>API Docs</span>
          {:else}
            <Search size={13} />
            <span>Cari</span>
          {/if}
        </button>

        <button
          type="button"
          onclick={() => showAboutModal = true}
          class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-900 dark:hover:text-white transition text-slate-700 dark:text-slate-200 font-semibold flex items-center gap-1.5 cursor-pointer shadow-2xs"
          title="Tentang CivitasID & Panduan / FAQ"
        >
          <HelpCircle size={14} class="text-sky-600 dark:text-sky-400" />
          <span class="hidden sm:inline">Tentang & FAQ</span>
        </button>

        <span class="hidden lg:inline-block font-mono bg-slate-100 dark:bg-[#1e293b] px-2.5 py-1 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold">v1.3.0</span>
        <a
          href="https://github.com/itzluthfi/civitas-id"
          target="_blank"
          rel="noreferrer"
          class="hidden sm:inline-block px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-[#1e293b] hover:bg-slate-200 dark:hover:bg-slate-700 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-900 dark:hover:text-white transition text-slate-700 dark:text-slate-200 font-semibold"
        >
          GitHub
        </a>
      </div>
    </div>
  </header>

  <!-- Mobile Segmented Controller (Native App Bar Style) -->
  {#if activeView === 'explorer'}
    <div class="lg:hidden border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a] p-2 sticky top-14 z-30">
      <div class="grid grid-cols-2 gap-1.5 bg-slate-100 dark:bg-[#1e293b] p-1 rounded-xl border border-slate-200 dark:border-slate-700">
        <button
          type="button"
          onclick={() => mobileTab = 'list'}
          class="py-2.5 px-3 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 {mobileTab === 'list' ? 'bg-sky-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'}"
        >
          <Search size={14} />
          <span>Hasil ({filteredResults.length})</span>
        </button>
        <button
          type="button"
          onclick={() => mobileTab = 'detail'}
          class="py-2.5 px-3 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-1.5 {mobileTab === 'detail' ? 'bg-sky-600 text-white shadow' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'}"
        >
          <FileText size={14} />
          <span class="truncate">
            {#if searchCategory === 'mhs'}
              Dokumen {mhsDetail ? `(${mhsDetail.nama.split(' ')[0]})` : ''}
            {:else if searchCategory === 'dosen'}
              Profil {dosenDetail ? `(${dosenDetail.nama_dosen.split(' ')[0]})` : ''}
            {:else}
              Kampus {ptDetail ? `(${ptDetail.nm_singkat || 'PT'})` : ''}
            {/if}
          </span>
        </button>
      </div>
    </div>
  {/if}

  <!-- Main Content Container -->
  <main class="flex-grow max-w-7xl w-full mx-auto px-4 py-5 flex flex-col gap-4">
    {#if activeView === 'docs'}
      <ApiDocs />
    {:else}
      <!-- Top Search Card & Multi-Category Switcher -->
      <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 shadow-sm dark:shadow-xl flex flex-col gap-3.5">
      <!-- Category Segmented Buttons -->
      <div class="flex items-center gap-2 border-b border-slate-200 dark:border-slate-700/80 pb-3">
        <span class="text-xs text-slate-500 dark:text-slate-300 font-mono font-semibold uppercase tracking-wider hidden sm:inline mr-1">Kategori:</span>
        <div class="grid grid-cols-3 sm:flex items-center gap-1.5 w-full sm:w-auto">
          <button
            type="button"
            onclick={() => handleCategorySwitch('mhs')}
            class="px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 {searchCategory === 'mhs' ? 'bg-sky-600 text-white shadow-md' : 'bg-slate-100 dark:bg-[#0f172a] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:text-white border border-slate-300 dark:border-slate-600 active:bg-slate-300 dark:active:bg-slate-800'}"
          >
            <GraduationCap size={15} />
            <span>Mahasiswa</span>
          </button>

          <button
            type="button"
            onclick={() => handleCategorySwitch('dosen')}
            class="px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 {searchCategory === 'dosen' ? 'bg-sky-600 text-white shadow-md' : 'bg-slate-100 dark:bg-[#0f172a] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:text-white border border-slate-300 dark:border-slate-600 active:bg-slate-300 dark:active:bg-slate-800'}"
          >
            <Users size={15} />
            <span>Dosen</span>
          </button>

          <button
            type="button"
            onclick={() => handleCategorySwitch('pt')}
            class="px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 {searchCategory === 'pt' ? 'bg-sky-600 text-white shadow-md' : 'bg-slate-100 dark:bg-[#0f172a] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:text-white border border-slate-300 dark:border-slate-600 active:bg-slate-300 dark:active:bg-slate-800'}"
          >
            <Building2 size={15} />
            <span class="truncate">Kampus & Stat</span>
          </button>
        </div>
      </div>

      <!-- Live Search Input Form (High-Contrast Non-Black Style) -->
      <form onsubmit={(e) => { e.preventDefault(); handleSearch(); }} class="flex flex-col sm:flex-row gap-2.5">
        <div class="relative flex-grow">
          <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-sky-600 dark:text-sky-400">
            <Search size={18} />
          </div>
          <input
            type="text"
            bind:value={searchQuery}
            placeholder={searchPlaceholder}
            class="w-full min-h-[50px] pl-11 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#0f172a] border-2 border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500 focus:border-sky-500 dark:focus:border-sky-400 focus:ring-4 focus:ring-sky-500/20 text-slate-900 dark:text-white placeholder-slate-400 text-sm font-medium transition shadow-xs"
          />
        </div>
        <button
          type="submit"
          disabled={isSearching}
          class="min-h-[50px] px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 active:scale-[0.98] text-white font-bold text-sm transition flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-md shadow-sky-600/10 flex-shrink-0"
        >
          {#if isSearching}
            <Loader2 size={16} class="animate-spin" />
            <span>Mencari...</span>
          {:else}
            <span>Cari Data</span>
          {/if}
        </button>
      </form>

      <!-- Preset Suggestions & Recent Searches -->
      <div class="flex flex-wrap items-center gap-2 pt-0.5 text-xs">
        <span class="text-slate-600 dark:text-slate-300 flex items-center gap-1 font-mono text-[11px] font-semibold">
          <History size={13} class="text-sky-600 dark:text-sky-400" />
          Contoh:
        </span>
        {#each CATEGORY_PRESETS[searchCategory] as item}
          <button
            type="button"
            onclick={() => handleSearch(item.query)}
            class="px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-600 hover:border-sky-500 text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white transition cursor-pointer text-[11px] font-medium active:bg-slate-200 dark:active:bg-slate-800"
          >
            {item.label}
          </button>
        {/each}

        {#if recentSearches.length > 0}
          <span class="text-slate-400 px-0.5 hidden sm:inline">|</span>
          <span class="text-slate-600 dark:text-slate-300 font-mono text-[11px] hidden sm:inline font-semibold">Riwayat:</span>
          {#each recentSearches as q}
            <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-[11px]">
              <button
                type="button"
                onclick={() => handleSearch(q)}
                class="hover:text-slate-900 dark:hover:text-white transition cursor-pointer font-medium"
              >
                {q}
              </button>
              <button
                type="button"
                onclick={(e) => removeRecentSearch(q, e)}
                class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer ml-0.5"
                title="Hapus riwayat"
              >
                <X size={11} />
              </button>
            </span>
          {/each}
          <button
            type="button"
            onclick={clearAllRecentSearches}
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-50 dark:bg-red-950/50 hover:bg-red-100 dark:hover:bg-red-900/60 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-white transition cursor-pointer text-[11px] font-semibold"
            title="Bersihkan seluruh riwayat pencarian"
          >
            <Trash2 size={11} />
            <span>Bersihkan</span>
          </button>
        {/if}
      </div>

      {#if searchError}
        <div class="p-3.5 rounded-xl bg-red-950/60 border border-red-800 text-red-200 text-xs font-semibold">
          {searchError}
        </div>
      {/if}
    </div>

    <!-- 2-Column Responsive Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
      <!-- Left Column (5 cols): Filters & Paginated Results -->
      <div class="lg:col-span-5 flex flex-col gap-3 {mobileTab === 'detail' ? 'hidden lg:flex' : 'flex'}">
        <!-- Interactive Filter & Select2 Box -->
        <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 flex flex-col gap-3.5 shadow-sm dark:shadow-lg">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-1.5 font-bold text-slate-900 dark:text-white">
              <Filter size={15} class="text-sky-600 dark:text-sky-400" />
              <span>Saring Hasil ({searchCategory.toUpperCase()})</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-slate-700 dark:text-slate-200 font-mono text-[11px] bg-slate-100 dark:bg-[#0f172a] px-2.5 py-0.5 rounded-md border border-slate-300 dark:border-slate-600 font-semibold">
                {filteredResults.length} / {totalRawResults}
              </span>
              {#if isAnyFilterActive}
                <button
                  type="button"
                  onclick={resetFilters}
                  class="text-[11px] text-amber-700 dark:text-amber-300 hover:text-amber-800 dark:hover:text-amber-200 flex items-center gap-1 cursor-pointer transition px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-700 font-semibold"
                >
                  <RotateCcw size={11} />
                  <span>Reset</span>
                </button>
              {/if}
            </div>
          </div>

          <!-- Quick keyword search inside current result set -->
          <div class="relative">
            <input
              type="text"
              bind:value={localKeyword}
              placeholder="Saring teks dalam daftar hasil..."
              class="w-full min-h-[42px] px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 focus:border-sky-500 dark:focus:border-sky-400 text-xs text-slate-900 dark:text-white placeholder-slate-400 font-medium focus:outline-none"
            />
          </div>

          <!-- Select2-style Comboboxes (For Mahasiswa & Dosen) -->
          {#if searchCategory === 'mhs' || searchCategory === 'dosen'}
            <div class="grid grid-cols-1 gap-2.5">
              <SearchableSelect
                label="Perguruan Tinggi"
                placeholder="Semua Kampus"
                options={kampusOptions}
                bind:value={filterKampus}
                icon={Building2}
              />

              <SearchableSelect
                label="Program Studi"
                placeholder="Semua Prodi"
                options={prodiOptions}
                bind:value={filterProdi}
                icon={BookOpen}
              />
            </div>
          {/if}

          <!-- Sorting Controls & Page Size -->
          <div class="flex items-center justify-between gap-2 pt-2.5 border-t border-slate-200 dark:border-slate-700/80 text-[11px]">
            <div class="flex items-center gap-1.5 text-slate-700 dark:text-slate-200 flex-grow font-semibold">
              <ArrowUpDown size={13} class="text-sky-600 dark:text-sky-400 flex-shrink-0" />
              <select
                bind:value={sortBy}
                class="w-full px-2.5 py-2 rounded-lg bg-slate-50 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 text-[11px] text-slate-900 dark:text-slate-100 font-medium focus:outline-none focus:border-sky-500"
              >
                <option value="default">Relevansi Asli PDDIKTI</option>
                <option value="name-asc">Nama (A - Z)</option>
                <option value="name-desc">Nama (Z - A)</option>
                <option value="code-asc">
                  {searchCategory === 'mhs' ? 'NIM' : searchCategory === 'dosen' ? 'NIDN' : 'Kode PT'} (Terkecil - Terbesar)
                </option>
                <option value="code-desc">
                  {searchCategory === 'mhs' ? 'NIM' : searchCategory === 'dosen' ? 'NIDN' : 'Kode PT'} (Terbesar - Terkecil)
                </option>
              </select>
            </div>

            <div class="flex items-center gap-1 text-slate-700 dark:text-slate-200 flex-shrink-0">
              <select
                bind:value={pageSize}
                class="px-2.5 py-2 rounded-lg bg-slate-50 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 text-[11px] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-sky-500 font-semibold"
              >
                <option value={6}>6 / hal</option>
                <option value={8}>8 / hal</option>
                <option value={12}>12 / hal</option>
                <option value={20}>20 / hal</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Result Cards List (Mobile-Optimized Cards) -->
        {#if paginatedResults.length === 0 && !isSearching}
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b]/70 p-8 text-center text-slate-500 dark:text-slate-300 text-xs font-medium shadow-sm">
            {#if totalRawResults > 0}
              Tidak ada data yang cocok dengan saringan aktif.
            {:else}
              Ketik kata kunci pada kolom pencarian di atas untuk memulai.
            {/if}
          </div>
        {:else}
          <div class="flex flex-col gap-2.5">
            {#each paginatedResults as item (item.id)}
              <div
                role="button"
                tabindex="0"
                onclick={() => selectItem(item.id)}
                onkeydown={(e) => { if (e.key === 'Enter') selectItem(item.id) }}
                class="p-3.5 rounded-2xl border transition cursor-pointer flex items-center justify-between gap-3 active:scale-[0.99] select-none shadow-xs {selectedId === item.id ? 'bg-sky-50 dark:bg-[#1e293b] border-2 border-sky-500 dark:border-sky-400 ring-2 ring-sky-500/20' : 'bg-white dark:bg-[#1e293b] border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 hover:bg-slate-50 dark:hover:bg-[#25334d] active:bg-slate-100 dark:active:bg-[#1e293b]'}"
              >
                <div class="flex flex-col gap-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-sm text-slate-900 dark:text-white truncate">{item.nama}</span>
                  </div>

                  {#if searchCategory === 'mhs'}
                    <div class="text-xs text-slate-700 dark:text-slate-200 flex items-center gap-1.5 truncate font-medium">
                      <Building2 size={13} class="text-sky-600 dark:text-sky-400 flex-shrink-0" />
                      <span class="truncate">{(item as MahasiswaSummary).sinkatan_pt || (item as MahasiswaSummary).nama_pt}</span>
                    </div>
                    <div class="text-xs text-slate-500 dark:text-slate-300 flex items-center gap-1.5 truncate">
                      <BookOpen size={13} class="text-slate-400 flex-shrink-0" />
                      <span class="truncate">{(item as MahasiswaSummary).nama_prodi}</span>
                    </div>
                  {:else if searchCategory === 'dosen'}
                    <div class="text-xs text-slate-700 dark:text-slate-200 flex items-center gap-1.5 truncate font-medium">
                      <Building2 size={13} class="text-sky-600 dark:text-sky-400 flex-shrink-0" />
                      <span class="truncate">{(item as DosenSummary).sinkatan_pt || (item as DosenSummary).nama_pt}</span>
                    </div>
                    <div class="text-xs text-slate-500 dark:text-slate-300 flex items-center gap-1.5 truncate">
                      <BookOpen size={13} class="text-slate-400 flex-shrink-0" />
                      <span class="truncate">{(item as DosenSummary).nama_prodi}</span>
                    </div>
                  {:else if searchCategory === 'pt'}
                    <div class="text-xs text-slate-700 dark:text-slate-200 flex items-center gap-1.5 truncate font-medium">
                      <Building2 size={13} class="text-sky-600 dark:text-sky-400 flex-shrink-0" />
                      <span class="truncate">{(item as PTSummary).nama_singkat || (item as PTSummary).nama}</span>
                    </div>
                  {/if}
                </div>

                <div class="flex flex-col items-end gap-1 flex-shrink-0">
                  <span class="text-xs font-mono font-semibold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-600 text-sky-700 dark:text-sky-300">
                    {#if searchCategory === 'mhs'}
                      {(item as MahasiswaSummary).nim}
                    {:else if searchCategory === 'dosen'}
                      {(item as DosenSummary).nidn || 'NIDN -'}
                    {:else}
                      {(item as PTSummary).kode}
                    {/if}
                  </span>
                  <ArrowRight size={15} class="text-slate-400 mt-1" />
                </div>
              </div>
            {/each}
          </div>

          <!-- Pagination Bar -->
          {#if totalPages > 1}
            <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1e293b] px-4 py-2.5 flex items-center justify-between text-xs text-slate-700 dark:text-slate-200 shadow-xs">
              <span class="font-mono text-[11px] font-semibold">
                Halaman {currentPage} dari {totalPages}
              </span>
              <div class="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={currentPage <= 1}
                  onclick={() => currentPage--}
                  class="min-h-[36px] px-3.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 hover:border-sky-500 disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition text-slate-800 dark:text-white flex items-center gap-1 font-semibold"
                >
                  <ChevronLeft size={14} />
                  <span class="hidden sm:inline">Prev</span>
                </button>
                <button
                  type="button"
                  disabled={currentPage >= totalPages}
                  onclick={() => currentPage++}
                  class="min-h-[36px] px-3.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 hover:border-sky-500 disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition text-slate-800 dark:text-white flex items-center gap-1 font-semibold"
                >
                  <span class="hidden sm:inline">Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          {/if}
        {/if}
      </div>

      <!-- Right Column (7 cols): Selected Details, Actions & Live Views -->
      <div class="lg:col-span-7 flex flex-col gap-4 {mobileTab === 'list' ? 'hidden lg:flex' : 'flex'}">
        {#if isLoadingDetail}
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-12 flex flex-col items-center justify-center gap-3 text-slate-700 dark:text-slate-200 shadow-sm">
            <Loader2 size={30} class="animate-spin text-sky-600 dark:text-sky-400" />
            <span class="text-xs font-semibold">Memuat data resmi dari PDDIKTI...</span>
          </div>

        <!-- MAHASISWA DETAIL VIEW -->
        {:else if searchCategory === 'mhs' && mhsDetail}
          <!-- Profile Summary Card with Pas Foto Upload & Copy Shortcuts -->
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 flex flex-col gap-4 shadow-sm dark:shadow-xl">
            <div class="flex flex-col sm:flex-row sm:items-start justify-between border-b border-slate-200 dark:border-slate-700 pb-3.5 gap-3">
              <div class="flex items-start gap-3.5">
                <!-- Pas Foto Box with Upload Trigger -->
                <div class="relative group flex-shrink-0">
                  <div class="w-16 h-20 sm:w-20 sm:h-24 rounded-xl border-2 border-slate-300 dark:border-slate-600 overflow-hidden bg-slate-100 dark:bg-[#0f172a] shadow-xs flex items-center justify-center">
                    {#if customStudentPhoto}
                      <img src={customStudentPhoto} alt="Pas Foto" class="w-full h-full object-cover" />
                    {:else}
                      <!-- Smart Academic Avatar based on Gender -->
                      <div class="w-full h-full flex flex-col items-center justify-center {mhsDetail.jenis_kelamin === 'P' ? 'bg-gradient-to-b from-sky-100 to-indigo-100 dark:from-slate-800 dark:to-slate-900 text-sky-800 dark:text-sky-300' : 'bg-gradient-to-b from-slate-100 to-sky-100 dark:from-slate-800 dark:to-slate-900 text-slate-700 dark:text-slate-300'}">
                        <svg class="w-9 h-9 sm:w-11 sm:h-11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                          {#if mhsDetail.jenis_kelamin === 'P'}
                            <path d="M12 14c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5z"/>
                            <path d="M5.5 21a6.5 6.5 0 0 1 13 0"/>
                          {:else}
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                          {/if}
                        </svg>
                        <span class="text-[8px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-0.5">Pas Foto</span>
                      </div>
                    {/if}
                  </div>

                  <!-- Upload Label / Button overlay -->
                  <label class="absolute -bottom-1 -right-1 p-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white shadow cursor-pointer transition flex items-center justify-center" title="Unggah pas foto untuk KTM & SKMA">
                    <Camera size={13} />
                    <input type="file" accept="image/*" class="hidden" onchange={handlePhotoUpload} />
                  </label>
                </div>

                <div>
                  <div class="text-[10px] text-sky-600 dark:text-sky-400 uppercase tracking-wider font-bold font-mono">Profil Mahasiswa PDDIKTI</div>
                  <div class="flex items-center gap-2 mt-0.5">
                    <h2 class="text-lg sm:text-xl font-bold text-slate-900 dark:text-white">{mhsDetail.nama}</h2>
                    <button
                      type="button"
                      onclick={() => copyToClipboard(mhsDetail!.nama, 'nama')}
                      class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-1"
                      title="Salin Nama"
                    >
                      {#if copiedField === 'nama'}
                        <Check size={15} class="text-emerald-600 dark:text-emerald-400" />
                      {:else}
                        <Copy size={15} />
                      {/if}
                    </button>
                  </div>
                  <div class="flex items-center gap-2 mt-0.5 text-xs font-mono text-slate-600 dark:text-slate-200">
                    <span class="font-semibold text-sky-700 dark:text-sky-300">NIM: {mhsDetail.nim}</span>
                    <button
                      type="button"
                      onclick={() => copyToClipboard(mhsDetail!.nim, 'nim')}
                      class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-0.5"
                      title="Salin NIM"
                    >
                      {#if copiedField === 'nim'}
                        <Check size={13} class="text-emerald-600 dark:text-emerald-400" />
                      {:else}
                        <Copy size={13} />
                      {/if}
                    </button>
                  </div>

                  <!-- Photo Action Hint -->
                  <div class="flex items-center gap-2 mt-1.5 text-[11px]">
                    {#if customStudentPhoto}
                      <span class="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 size={12} />
                        Foto aktif di KTM & SKMA
                      </span>
                      <button
                        type="button"
                        onclick={removeStudentPhoto}
                        class="text-rose-600 dark:text-rose-400 hover:underline cursor-pointer flex items-center gap-0.5 font-semibold text-[10px]"
                      >
                        <Trash2 size={11} />
                        Hapus Foto
                      </button>
                    {:else}
                      <label class="text-sky-600 dark:text-sky-400 hover:underline cursor-pointer flex items-center gap-1 font-semibold">
                        <Upload size={11} />
                        Unggah Pas Foto (KTM/SKMA)
                        <input type="file" accept="image/*" class="hidden" onchange={handlePhotoUpload} />
                      </label>
                    {/if}
                  </div>
                </div>
              </div>

              <div>
                <span class="px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/90 border border-emerald-300 dark:border-emerald-600 text-emerald-800 dark:text-emerald-300 text-xs font-semibold inline-flex items-center gap-1.5 shadow-2xs">
                  <CheckCircle2 size={13} />
                  {mhsDetail.status_saat_ini}
                </span>
              </div>
            </div>

            <!-- Detail Grid (High-Contrast Non-Black Boxes) -->
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Perguruan Tinggi</div>
                <div class="font-bold text-slate-900 dark:text-white line-clamp-2">{mhsDetail.nama_pt}</div>
                {#if mhsDetail.kode_pt}
                  <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">Kode: {mhsDetail.kode_pt}</div>
                {/if}
              </div>
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Program Studi</div>
                <div class="font-bold text-slate-900 dark:text-white line-clamp-2">{mhsDetail.prodi} ({mhsDetail.jenjang})</div>
                {#if mhsDetail.kode_prodi}
                  <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">Kode: {mhsDetail.kode_prodi}</div>
                {/if}
              </div>
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Tanggal Masuk</div>
                <div class="font-bold text-slate-700 dark:text-slate-200">{formatIndoDate(mhsDetail.tanggal_masuk)}</div>
                {#if mhsDetail.jenis_daftar}
                  <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{mhsDetail.jenis_daftar}</div>
                {/if}
              </div>
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Jenis Kelamin</div>
                <div class="font-bold text-slate-900 dark:text-white">
                  {mhsDetail.jenis_kelamin === 'L' ? 'Laki-laki' : mhsDetail.jenis_kelamin === 'P' ? 'Perempuan' : mhsDetail.jenis_kelamin || '-'}
                </div>
              </div>
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Jenjang Pendidikan</div>
                <div class="font-bold text-slate-900 dark:text-white">{mhsDetail.jenjang || 'Sarjana'}</div>
              </div>
              <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col justify-between">
                <div class="text-sky-600 dark:text-sky-400 mb-1 text-[11px] font-mono font-semibold uppercase tracking-wider">Verifikasi PDDIKTI</div>
                <div class="flex items-center gap-2">
                  <a
                    href={mhsDetail.verify_url}
                    target="_blank"
                    rel="noreferrer"
                    class="font-bold text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300 flex items-center gap-1 transition"
                  >
                    <span>Buka Portal</span>
                    <ExternalLink size={12} />
                  </a>
                  <button
                    type="button"
                    onclick={() => copyToClipboard(mhsDetail!.verify_url || '', 'url')}
                    class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-0.5"
                    title="Salin Link PDDIKTI"
                  >
                    {#if copiedField === 'url'}
                      <Check size={12} class="text-emerald-600 dark:text-emerald-400" />
                    {:else}
                      <Copy size={12} />
                    {/if}
                  </button>
                </div>
              </div>
            </div>

            <!-- Validasi Akademik Lanjutan & Repositori Tugas Akhir (RAMA & SIVIL) -->
            <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Validasi Lanjutan & Repositori Tugas Akhir</div>
                <div class="text-slate-600 dark:text-slate-300 text-xs mt-0.5">Penelusuran skripsi/tesis di RAMA Repositori Nasional & verifikasi ijazah elektronik di SIVIL.</div>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <a
                  href={mhsDetail.rama_search_url || `https://rama.kemdiktisaintek.go.id/search?q=${encodeURIComponent(mhsDetail.nama)}`}
                  target="_blank"
                  rel="noreferrer"
                  class="px-2.5 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-700 text-indigo-800 dark:text-indigo-200 font-bold text-xs flex items-center gap-1.5 transition hover:bg-indigo-100 shadow-2xs"
                  title="Cari naskah skripsi / karya ilmiah mahasiswa di RAMA Kemdiktisaintek"
                >
                  <BookOpen size={12} class="text-indigo-600 dark:text-indigo-400" />
                  <span>Skripsi RAMA</span>
                  <ExternalLink size={10} />
                </a>
                <a
                  href={mhsDetail.sivil_url || "https://ijazah.kemdiktisaintek.go.id"}
                  target="_blank"
                  rel="noreferrer"
                  class="px-2.5 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200 font-bold text-xs flex items-center gap-1.5 transition hover:bg-emerald-100 shadow-2xs"
                  title="Verifikasi keabsahan nomor ijazah nasional (NIN) di SIVIL"
                >
                  <Shield size={12} class="text-emerald-600 dark:text-emerald-400" />
                  <span>Ijazah SIVIL</span>
                  <ExternalLink size={10} />
                </a>
                <a
                  href={mhsDetail.scholar_search_url || `https://scholar.google.com/scholar?q=${encodeURIComponent(mhsDetail.nama + ' ' + mhsDetail.nama_pt)}`}
                  target="_blank"
                  rel="noreferrer"
                  class="px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-[#1e293b] border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 font-semibold text-xs flex items-center gap-1.5 transition hover:bg-slate-200 dark:hover:bg-slate-700 shadow-2xs"
                  title="Cari publikasi atau paper ilmiah mahasiswa di Google Scholar"
                >
                  <Award size={12} class="text-sky-600 dark:text-sky-400" />
                  <span>Karya Ilmiah</span>
                  <ExternalLink size={10} />
                </a>
              </div>
            </div>
          </div>

          <!-- Document Generation & Action Panel -->
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 flex flex-col gap-4 shadow-sm dark:shadow-xl">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs text-sky-600 dark:text-sky-400 uppercase tracking-wider font-bold font-mono">Format Dokumen Dinamis</div>
                <p class="text-xs text-slate-600 dark:text-slate-200 mt-0.5 font-medium">Kop, stempel vektor, dan lambang otomatis sesuai kampus {mhsDetail.nama_pt}.</p>
              </div>
              {#if inlinePreviewUrl}
                <button
                  type="button"
                  onclick={() => showFullscreenModal = true}
                  class="min-h-[36px] px-3.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-[#0f172a] hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-xs"
                  title="Perbesar Pratinjau Layar Penuh"
                >
                  <Maximize2 size={13} class="text-sky-600 dark:text-sky-400" />
                  <span class="hidden sm:inline">Layar Penuh</span>
                </button>
              {/if}
            </div>

            <!-- Template Tabs (Large touch targets, high contrast) -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                onclick={() => onTemplateChange('skma_bilingual')}
                class="min-h-[52px] px-3 py-2.5 rounded-xl border text-xs font-bold text-center transition cursor-pointer flex flex-col items-center justify-center gap-1.5 active:scale-[0.98] {activeTemplate === 'skma_bilingual' ? 'bg-sky-50 dark:bg-sky-950 border-2 border-sky-500 dark:border-sky-400 text-sky-900 dark:text-sky-100 ring-2 ring-sky-500/20 shadow-xs' : 'bg-slate-50 dark:bg-[#0f172a] border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-500'}"
              >
                <Globe size={16} class={activeTemplate === 'skma_bilingual' ? 'text-sky-600 dark:text-sky-400' : 'text-slate-400'} />
                <span>SKMA Bilingual</span>
              </button>

              <button
                type="button"
                onclick={() => onTemplateChange('skma_id')}
                class="min-h-[52px] px-3 py-2.5 rounded-xl border text-xs font-bold text-center transition cursor-pointer flex flex-col items-center justify-center gap-1.5 active:scale-[0.98] {activeTemplate === 'skma_id' ? 'bg-sky-50 dark:bg-sky-950 border-2 border-sky-500 dark:border-sky-400 text-sky-900 dark:text-sky-100 ring-2 ring-sky-500/20 shadow-xs' : 'bg-slate-50 dark:bg-[#0f172a] border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-500'}"
              >
                <FileText size={16} class={activeTemplate === 'skma_id' ? 'text-sky-600 dark:text-sky-400' : 'text-slate-400'} />
                <span>SKMA Standar</span>
              </button>

              <button
                type="button"
                onclick={() => onTemplateChange('ktm')}
                class="min-h-[52px] px-3 py-2.5 rounded-xl border text-xs font-bold text-center transition cursor-pointer flex flex-col items-center justify-center gap-1.5 active:scale-[0.98] {activeTemplate === 'ktm' ? 'bg-sky-50 dark:bg-sky-950 border-2 border-sky-500 dark:border-sky-400 text-sky-900 dark:text-sky-100 ring-2 ring-sky-500/20 shadow-xs' : 'bg-slate-50 dark:bg-[#0f172a] border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-500'}"
              >
                <CreditCard size={16} class={activeTemplate === 'ktm' ? 'text-sky-600 dark:text-sky-400' : 'text-slate-400'} />
                <span>KTM Digital</span>
              </button>

              <button
                type="button"
                onclick={() => onTemplateChange('transcript')}
                class="min-h-[52px] px-3 py-2.5 rounded-xl border text-xs font-bold text-center transition cursor-pointer flex flex-col items-center justify-center gap-1.5 active:scale-[0.98] {activeTemplate === 'transcript' ? 'bg-sky-50 dark:bg-sky-950 border-2 border-sky-500 dark:border-sky-400 text-sky-900 dark:text-sky-100 ring-2 ring-sky-500/20 shadow-xs' : 'bg-slate-50 dark:bg-[#0f172a] border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:border-slate-400 dark:hover:border-slate-500'}"
              >
                <FileSpreadsheet size={16} class={activeTemplate === 'transcript' ? 'text-sky-600 dark:text-sky-400' : 'text-slate-400'} />
                <span>Transkrip</span>
              </button>
            </div>

            <!-- Status Sumber Data Dokumen -->
            {#if activeTemplate === 'transcript'}
              <div class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
                <Info size={16} class="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div class="leading-relaxed">
                  <div class="font-bold">Keterangan Sumber Data Transkrip:</div>
                  <div class="mt-0.5 text-amber-800 dark:text-amber-300">
                    • <strong>Identitas Mahasiswa:</strong> 100% Data Riil & Sah dari PDDIKTI Kemdiktisaintek.<br>
                    • <strong>Daftar Mata Kuliah:</strong> Estimasi kurikulum standar program studi (Pemerintah/PDDIKTI tidak membuka nilai SIAKAD privat mahasiswa ke publik).
                  </div>
                </div>
              </div>
            {:else}
              <div class="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-900 dark:text-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 size={15} class="text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span><strong>100% Data Riil:</strong> Seluruh identitas & keaktifan pada dokumen ini ditarik langsung dari pangkalan data resmi PDDIKTI.</span>
              </div>
            {/if}

            <!-- Download Action Buttons (Thumb-friendly full targets) -->
            <div class="flex flex-col sm:flex-row gap-2.5 pt-1">
              <button
                type="button"
                onclick={() => handleDownload('pdf')}
                disabled={isDownloading !== null || isBatchDownloading}
                class="min-h-[50px] flex-1 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 active:scale-[0.98] text-white font-bold text-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 shadow-md shadow-sky-600/10"
              >
                {#if isDownloading === `${activeTemplate}-pdf`}
                  <Loader2 size={16} class="animate-spin" />
                  <span>Merender PDF...</span>
                {:else}
                  <Download size={16} />
                  <span>Unduh Dokumen PDF</span>
                {/if}
              </button>

              <button
                type="button"
                onclick={() => handleDownload('png')}
                disabled={isDownloading !== null || isBatchDownloading}
                class="min-h-[50px] flex-1 px-4 rounded-xl bg-slate-100 dark:bg-[#0f172a] hover:bg-slate-200 dark:hover:bg-slate-700 active:scale-[0.98] border border-slate-300 dark:border-slate-600 text-slate-800 dark:text-white font-bold text-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 shadow-xs"
              >
                {#if isDownloading === `${activeTemplate}-png`}
                  <Loader2 size={16} class="animate-spin" />
                  <span>Merender PNG...</span>
                {:else}
                  <Download size={16} />
                  <span>Unduh Gambar PNG</span>
                {/if}
              </button>

              <button
                type="button"
                onclick={handleBatchDownload}
                disabled={isBatchDownloading || isDownloading !== null}
                class="min-h-[50px] px-4 rounded-xl bg-indigo-50 dark:bg-indigo-950 hover:bg-indigo-100 dark:hover:bg-indigo-900 active:scale-[0.98] border border-indigo-300 dark:border-indigo-600 text-indigo-800 dark:text-indigo-200 font-bold text-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 flex-shrink-0 shadow-xs"
                title="Unduh seluruh 4 dokumen sekaligus"
              >
                {#if isBatchDownloading}
                  <Loader2 size={16} class="animate-spin text-amber-500 dark:text-amber-400" />
                  <span>Mengunduh...</span>
                {:else}
                  <Archive size={16} class="text-amber-600 dark:text-amber-400" />
                  <span>Paket Lengkap (4)</span>
                {/if}
              </button>
            </div>

            <!-- Inline Live Document Preview Card -->
            <div class="mt-2 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] p-3.5 sm:p-4 flex flex-col gap-2">
              <div class="flex items-center justify-between text-xs text-slate-700 dark:text-slate-200 px-1">
                <span class="font-bold flex items-center gap-1.5 text-slate-900 dark:text-white">
                  <Eye size={14} class="text-sky-600 dark:text-sky-400" />
                  Pratinjau Langsung ({activeTemplate.toUpperCase()})
                </span>
                <span class="text-[11px] text-slate-500 dark:text-slate-400 font-mono font-medium">Render Otomatis</span>
              </div>

              <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-[#1e293b]/70 min-h-[300px] flex items-center justify-center overflow-hidden p-3">
                {#if isGeneratingInlinePreview}
                  <div class="flex flex-col items-center gap-2 text-slate-600 dark:text-slate-300 py-12">
                    <Loader2 size={26} class="animate-spin text-sky-600 dark:text-sky-400" />
                    <span class="text-xs font-semibold">Merender dokumen dinamis...</span>
                  </div>
                {:else if inlinePreviewUrl}
                  <div class="w-full max-w-lg bg-white rounded-lg shadow-2xl overflow-hidden border-2 border-slate-300 dark:border-slate-500">
                    <img
                      src={inlinePreviewUrl}
                      alt="Pratinjau Dokumen"
                      class="w-full h-auto block"
                    />
                  </div>
                {:else}
                  <div class="text-slate-500 dark:text-slate-400 text-xs font-medium">Pratinjau belum dimuat.</div>
                {/if}
              </div>
            </div>
          </div>

        <!-- DOSEN DETAIL VIEW -->
        {:else if searchCategory === 'dosen' && dosenDetail}
          <div class="flex flex-col gap-4">
            <!-- Header Banner & Quick Status Card -->
            <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-6 flex flex-col gap-4 shadow-sm dark:shadow-xl">
              <div class="flex flex-col sm:flex-row sm:items-start justify-between border-b border-slate-200 dark:border-slate-700 pb-4 gap-3">
                <div class="flex items-start gap-3.5">
                  <!-- Dosen Avatar Box -->
                  <div class="w-14 h-16 sm:w-16 sm:h-20 rounded-xl border-2 border-slate-300 dark:border-slate-600 overflow-hidden bg-gradient-to-b from-sky-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 shadow-xs flex flex-col items-center justify-center flex-shrink-0 text-sky-800 dark:text-sky-300 relative">
                    {#if dosenDetail.foto_url}
                      <img
                        src={dosenDetail.foto_url}
                        alt={dosenDetail.nama_dosen}
                        class="w-full h-full object-cover"
                        onerror={(e) => {
                          // Fallback if image fails to load
                          const target = e.currentTarget as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                    {:else}
                      <User size={28} />
                      <span class="text-[8px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-0.5">Dosen</span>
                    {/if}
                  </div>

                  <div>
                    <div class="text-[10px] text-sky-600 dark:text-sky-400 uppercase tracking-wider font-bold font-mono">Profil Tenaga Pendidik / Dosen</div>
                    <div class="flex items-center gap-2 mt-0.5">
                      <h2 class="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white">{dosenDetail.nama_dosen}</h2>
                      <button
                        type="button"
                        onclick={() => copyToClipboard(dosenDetail!.nama_dosen, 'dosen_nama')}
                        class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-1"
                        title="Salin Nama Dosen"
                      >
                        {#if copiedField === 'dosen_nama'}
                          <Check size={16} class="text-emerald-600 dark:text-emerald-400" />
                        {:else}
                          <Copy size={16} />
                        {/if}
                      </button>
                    </div>
                    <div class="flex flex-wrap items-center gap-2 mt-1 text-xs font-mono text-slate-600 dark:text-slate-200">
                      <span class="font-bold text-sky-700 dark:text-sky-300">Homebase: {dosenDetail.nama_pt}</span>
                      {#if dosenDetail.nama_prodi}
                        <span class="text-slate-400">•</span>
                        <span class="text-slate-700 dark:text-slate-300">{dosenDetail.nama_prodi}</span>
                      {/if}
                    </div>

                    <!-- External Author Research Profile Links (SINTA & Google Scholar) -->
                    <div class="flex flex-wrap items-center gap-2 mt-2">
                      <a
                        href={dosenDetail.sinta_url || `https://sinta.kemdiktisaintek.go.id/authors?q=${encodeURIComponent(dosenDetail.nama_dosen)}`}
                        target="_blank"
                        rel="noreferrer"
                        class="px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-700 text-indigo-800 dark:text-indigo-200 text-[11px] font-bold inline-flex items-center gap-1 hover:bg-indigo-100 transition shadow-2xs"
                        title="Lihat profil author, skor SINTA, dan publikasi terverifikasi di Kemdiktisaintek"
                      >
                        <Award size={12} class="text-indigo-600 dark:text-indigo-400" />
                        <span>{dosenDetail.sinta_id ? `Profil SINTA #${dosenDetail.sinta_id}` : 'Cari di SINTA'}</span>
                        <ExternalLink size={10} />
                      </a>
                      <a
                        href={dosenDetail.google_scholar_url || `https://scholar.google.com/citations?view_op=search_authors&mauthors=${encodeURIComponent(dosenDetail.nama_dosen)}`}
                        target="_blank"
                        rel="noreferrer"
                        class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 text-[11px] font-semibold inline-flex items-center gap-1 hover:bg-slate-200 dark:hover:bg-slate-800 transition shadow-2xs"
                        title="Lihat sitasi dan indeks riset di Google Scholar"
                      >
                        <BookOpen size={12} class="text-sky-600 dark:text-sky-400" />
                        <span>Google Scholar</span>
                        <ExternalLink size={10} />
                      </a>
                    </div>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  {#if dosenDetail.status_aktivitas}
                    <span class="px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/90 border border-emerald-300 dark:border-emerald-600 text-emerald-800 dark:text-emerald-300 text-xs font-bold inline-flex items-center gap-1.5 shadow-2xs">
                      <CheckCircle2 size={13} />
                      {dosenDetail.status_aktivitas}
                    </span>
                  {/if}
                  {#if dosenDetail.status_ikatan_kerja}
                    <span class="px-3 py-1 rounded-full bg-sky-50 dark:bg-sky-950/90 border border-sky-300 dark:border-sky-600 text-sky-800 dark:text-sky-300 text-xs font-bold inline-flex items-center gap-1.5">
                      {dosenDetail.status_ikatan_kerja}
                    </span>
                  {/if}
                </div>
              </div>

              <!-- Quick Metadata Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Jenis Kelamin</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.jenis_kelamin || '-'}</div>
                </div>
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Pendidikan Tertinggi</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.pendidikan_tertinggi || '-'}</div>
                </div>
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Jabatan Akademik</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.jabatan_akademik || 'Dosen Pengajar'}</div>
                </div>
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Ikatan Kerja</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.status_ikatan_kerja || '-'}</div>
                </div>
              </div>

              <!-- SINTA Metrik & Indeks Sitasi (Tersinkronisasi Otomatis dari SINTA Kemdiktisaintek) -->
              {#if dosenDetail.sinta_id || dosenDetail.sinta_score_overall || dosenDetail.scopus_h_index !== null && dosenDetail.scopus_h_index !== undefined}
                <div class="rounded-2xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20 p-4 flex flex-col gap-3 shadow-xs">
                  <div class="flex items-center justify-between border-b border-indigo-100 dark:border-indigo-900/50 pb-2">
                    <div class="flex items-center gap-2">
                      <Award size={16} class="text-indigo-600 dark:text-indigo-400" />
                      <h3 class="font-bold text-sm text-slate-900 dark:text-white">Metrik Riset & Publikasi Ilmiah (SINTA)</h3>
                    </div>
                    {#if dosenDetail.sinta_id}
                      <span class="text-[11px] font-mono font-bold text-indigo-700 dark:text-indigo-300 bg-white dark:bg-[#0f172a] px-2 py-0.5 rounded border border-indigo-200 dark:border-indigo-800">
                        SINTA ID: {dosenDetail.sinta_id}
                      </span>
                    {/if}
                  </div>

                  <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    <div class="p-2.5 rounded-xl bg-white dark:bg-[#0f172a] border border-indigo-100 dark:border-indigo-900/50">
                      <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase font-semibold">SINTA Score 3Yr</div>
                      <div class="text-base font-bold text-indigo-700 dark:text-indigo-300 mt-0.5">{dosenDetail.sinta_score_3yr || '-'}</div>
                    </div>
                    <div class="p-2.5 rounded-xl bg-white dark:bg-[#0f172a] border border-indigo-100 dark:border-indigo-900/50">
                      <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase font-semibold">SINTA Score Overall</div>
                      <div class="text-base font-bold text-indigo-700 dark:text-indigo-300 mt-0.5">{dosenDetail.sinta_score_overall || '-'}</div>
                    </div>
                    <div class="p-2.5 rounded-xl bg-white dark:bg-[#0f172a] border border-indigo-100 dark:border-indigo-900/50">
                      <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase font-semibold">Scopus H-Index</div>
                      <div class="text-base font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.scopus_h_index !== null && dosenDetail.scopus_h_index !== undefined ? dosenDetail.scopus_h_index : '-'}</div>
                    </div>
                    <div class="p-2.5 rounded-xl bg-white dark:bg-[#0f172a] border border-indigo-100 dark:border-indigo-900/50">
                      <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase font-semibold">Scholar H-Index</div>
                      <div class="text-base font-bold text-slate-900 dark:text-white mt-0.5">{dosenDetail.google_scholar_h_index !== null && dosenDetail.google_scholar_h_index !== undefined ? dosenDetail.google_scholar_h_index : '-'}</div>
                    </div>
                  </div>
                </div>
              {/if}
            </div>

            <!-- Riwayat Pendidikan (Study History) -->
            <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 flex flex-col gap-3 shadow-sm">
              <div class="flex items-center gap-2 border-b border-slate-200 dark:border-slate-700 pb-2.5">
                <GraduationCap size={16} class="text-sky-600 dark:text-sky-400" />
                <h3 class="font-bold text-sm text-slate-900 dark:text-white">Riwayat Pendidikan</h3>
              </div>
              {#if dosenDetail.study_history && dosenDetail.study_history.length > 0}
                <div class="flex flex-col gap-2">
                  {#each dosenDetail.study_history as sh}
                    <div class="p-3 rounded-xl bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                      <div class="flex items-center gap-3">
                        <span class="w-9 h-9 rounded-lg bg-sky-100 dark:bg-sky-950 border border-sky-300 dark:border-sky-700 text-sky-800 dark:text-sky-300 font-bold flex items-center justify-center font-mono text-xs flex-shrink-0">
                          {sh.jenjang || 'PT'}
                        </span>
                        <div>
                          <div class="font-bold text-slate-900 dark:text-white">{sh.nama_pt || 'Perguruan Tinggi'}</div>
                          <div class="text-slate-500 dark:text-slate-400 text-[11px]">
                            {sh.gelar_akademik ? `${sh.gelar_akademik} (${sh.singkatan_gelar || ''})` : ''} {sh.nama_prodi ? `• ${sh.nama_prodi}` : ''}
                          </div>
                        </div>
                      </div>
                      <div class="flex items-center gap-2 sm:text-right font-mono text-[11px] text-slate-600 dark:text-slate-300">
                        <span>Lulus: <strong class="text-slate-900 dark:text-white">{sh.tahun_lulus || '-'}</strong></span>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
                  Tidak ada riwayat pendidikan yang tercatat di PDDIKTI.
                </div>
              {/if}
            </div>

            <!-- Riwayat Mengajar (Teaching History) -->
            <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 flex flex-col gap-3 shadow-sm">
              <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2.5">
                <div class="flex items-center gap-2">
                  <BookOpen size={16} class="text-sky-600 dark:text-sky-400" />
                  <h3 class="font-bold text-sm text-slate-900 dark:text-white">Riwayat Mengajar</h3>
                </div>
                {#if dosenDetail.teaching_history && dosenDetail.teaching_history.length > 0}
                  <span class="text-[11px] font-mono text-slate-500 dark:text-slate-400 font-semibold">
                    {dosenDetail.teaching_history.length} Kelas Tercatat
                  </span>
                {/if}
              </div>

              {#if dosenDetail.teaching_history && dosenDetail.teaching_history.length > 0}
                <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 max-h-80 overflow-y-auto">
                  <table class="w-full text-left text-xs border-collapse">
                    <thead class="sticky top-0 bg-slate-100 dark:bg-[#0f172a] text-slate-700 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 text-[11px]">
                      <tr>
                        <th class="p-2.5">Semester</th>
                        <th class="p-2.5">Kode Matkul</th>
                        <th class="p-2.5">Mata Kuliah</th>
                        <th class="p-2.5 text-center">Kelas</th>
                        <th class="p-2.5">Perguruan Tinggi</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200 dark:divide-slate-800 bg-white dark:bg-[#1e293b]">
                      {#each dosenDetail.teaching_history as th}
                        <tr class="hover:bg-slate-50 dark:hover:bg-[#25334d] transition-colors">
                          <td class="p-2.5 font-mono text-[11px] text-slate-700 dark:text-slate-300">{th.nama_semester}</td>
                          <td class="p-2.5 font-mono text-[11px] font-semibold text-sky-700 dark:text-sky-300">{th.kode_matkul}</td>
                          <td class="p-2.5 font-bold text-slate-900 dark:text-white">{th.nama_matkul}</td>
                          <td class="p-2.5 text-center font-mono font-semibold text-slate-700 dark:text-slate-300">{th.nama_kelas}</td>
                          <td class="p-2.5 text-slate-600 dark:text-slate-300 text-[11px] truncate max-w-xs">{th.nama_pt || dosenDetail.nama_pt}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {:else}
                <div class="text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
                  Tidak ada riwayat aktivitas mengajar yang tercatat di PDDIKTI.
                </div>
              {/if}
            </div>

            <!-- Official Portal Link -->
            {#if dosenDetail.verify_url}
              <div class="rounded-xl bg-slate-50 dark:bg-[#1e293b] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs flex items-center justify-between">
                <div>
                  <div class="text-sky-600 dark:text-sky-400 text-[11px] font-mono font-semibold uppercase tracking-wider">Verifikasi Data Resmi PDDIKTI</div>
                  <div class="text-slate-600 dark:text-slate-300 text-xs mt-0.5">Tervalidasi langsung pada direktori Dosen Kemdiktisaintek RI.</div>
                </div>
                <a
                  href={dosenDetail.verify_url}
                  target="_blank"
                  rel="noreferrer"
                  class="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-xs"
                >
                  <span>Buka Portal Resmi</span>
                  <ExternalLink size={13} />
                </a>
              </div>
            {/if}
          </div>

        <!-- PERGURUAN TINGGI & STATISTIK DETAIL VIEW -->
        {:else if searchCategory === 'pt' && ptDetail}
          <div class="flex flex-col gap-4">
            <!-- Header Banner & Quick Status Card -->
            <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-6 flex flex-col gap-4 shadow-sm dark:shadow-xl">
              <div class="flex flex-col sm:flex-row sm:items-start justify-between border-b border-slate-200 dark:border-slate-700 pb-4 gap-3">
                <div>
                  <div class="text-[10px] text-sky-600 dark:text-sky-400 uppercase tracking-wider font-bold font-mono">Profil Perguruan Tinggi Resmi</div>
                  <div class="flex items-center gap-2 mt-0.5">
                    <h2 class="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white">{ptDetail.nama_pt}</h2>
                    <button
                      type="button"
                      onclick={() => copyToClipboard(ptDetail!.nama_pt, 'pt_nama')}
                      class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-1"
                      title="Salin Nama Kampus"
                    >
                      {#if copiedField === 'pt_nama'}
                        <Check size={16} class="text-emerald-600 dark:text-emerald-400" />
                      {:else}
                        <Copy size={16} />
                      {/if}
                    </button>
                  </div>
                  <div class="flex flex-wrap items-center gap-2 mt-1 text-xs font-mono text-slate-600 dark:text-slate-200">
                    <span class="font-bold text-sky-700 dark:text-sky-300">Kode PT: {ptDetail.kode_pt}</span>
                    {#if ptDetail.nm_singkat}
                      <span class="text-slate-500 font-semibold">• {ptDetail.nm_singkat}</span>
                    {/if}
                    {#if ptDetail.kelompok}
                      <span class="text-slate-400">•</span>
                      <span class="text-slate-600 dark:text-slate-300">{ptDetail.kelompok}</span>
                    {/if}
                    {#if ptDetail.pembina}
                      <span class="text-slate-400">•</span>
                      <span class="text-slate-600 dark:text-slate-300">{ptDetail.pembina}</span>
                    {/if}
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  <!-- Status Aktif Badge -->
                  <span class="px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5 shadow-2xs {ptDetail.status_pt === 'Aktif' || !ptDetail.status_pt ? 'bg-emerald-50 dark:bg-emerald-950/90 border border-emerald-300 dark:border-emerald-600 text-emerald-800 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-950 border border-rose-300 dark:border-rose-600 text-rose-800 dark:text-rose-300'}">
                    <span class="w-1.5 h-1.5 rounded-full {ptDetail.status_pt === 'Aktif' || !ptDetail.status_pt ? 'bg-emerald-500' : 'bg-rose-500'}"></span>
                    Status: {ptDetail.status_pt || 'Aktif'}
                  </span>
                  <!-- Akreditasi Badge -->
                  {#if ptDetail.akreditasi_pt}
                    <span class="px-3 py-1 rounded-full bg-amber-50 dark:bg-amber-950/90 border border-amber-300 dark:border-amber-600 text-amber-800 dark:text-amber-300 text-xs font-bold inline-flex items-center gap-1 shadow-2xs">
                      <Award size={13} />
                      Akreditasi: {ptDetail.akreditasi_pt}
                    </span>
                  {/if}
                </div>
              </div>

              <!-- Campus Quick Metadata Grid (Kode, Status, Akreditasi, Biaya Kuliah, Tanggal Berdiri, SK Pendirian) -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Kode PT</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5 font-mono text-sm">{ptDetail.kode_pt}</div>
                </div>

                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Biaya Kuliah (Range)</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">
                    {ptDetail.biaya_kuliah ? `Rp${ptDetail.biaya_kuliah}` : 'Rp1 - 3.600.000'}
                  </div>
                </div>

                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">Tanggal Berdiri</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5">{formatIndoDate(ptDetail.tgl_berdiri_pt)}</div>
                </div>

                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs">
                  <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider">SK Pendirian</div>
                  <div class="font-bold text-slate-900 dark:text-white mt-0.5 truncate" title={ptDetail.sk_pendirian_sp || '-'}>
                    {ptDetail.sk_pendirian_sp || '-'}
                  </div>
                  {#if ptDetail.tgl_sk_pendirian_sp}
                    <div class="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{formatIndoDate(ptDetail.tgl_sk_pendirian_sp)}</div>
                  {/if}
                </div>
              </div>

              <!-- Kontak, Alamat, Pimpinan & Peta Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                <!-- Kontak & Website -->
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col justify-between">
                  <div>
                    <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1">
                      <Mail size={12} />
                      <span>Kontak & Website</span>
                    </div>
                    <div class="flex flex-col gap-1 text-slate-800 dark:text-slate-200 mt-1">
                      {#if ptDetail.email}
                        <div class="flex items-center gap-1.5 truncate">
                          <span class="text-slate-500 dark:text-slate-400 text-[11px]">Email:</span>
                          <a href={`mailto:${ptDetail.email}`} class="font-semibold text-sky-600 dark:text-sky-400 hover:underline truncate">
                            {ptDetail.email}
                          </a>
                        </div>
                      {/if}
                      {#if ptDetail.website}
                        <div class="flex items-center gap-1.5 truncate">
                          <span class="text-slate-500 dark:text-slate-400 text-[11px]">Web:</span>
                          <a href={ptDetail.website.startsWith('http') ? ptDetail.website : `https://${ptDetail.website}`} target="_blank" rel="noreferrer" class="font-semibold text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-1 truncate">
                            <span class="truncate">{ptDetail.website}</span>
                            <ExternalLink size={11} class="flex-shrink-0" />
                          </a>
                        </div>
                      {/if}
                      <div class="flex items-center gap-3 text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">
                        {#if ptDetail.no_tel}
                          <span>Telp: <strong class="text-slate-900 dark:text-white">{ptDetail.no_tel}</strong></span>
                        {/if}
                        {#if ptDetail.no_fax && ptDetail.no_fax !== '0'}
                          <span>Fax: <strong class="text-slate-900 dark:text-white">{ptDetail.no_fax}</strong></span>
                        {/if}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Alamat Kampus -->
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col justify-between">
                  <div>
                    <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1">
                      <MapPin size={12} />
                      <span>Alamat Kampus</span>
                    </div>
                    <div class="font-medium text-slate-800 dark:text-slate-200 leading-relaxed mt-1">
                      {ptDetail.alamat || '-'}
                      {#if ptDetail.kecamatan_pt}
                        , {ptDetail.kecamatan_pt}
                      {/if}
                      {#if ptDetail.kab_kota_pt}
                        , {ptDetail.kab_kota_pt}
                      {/if}
                      {#if ptDetail.provinsi_pt}
                        , {ptDetail.provinsi_pt}
                      {/if}
                      {#if ptDetail.kode_pos}
                        (Kode Pos: {ptDetail.kode_pos})
                      {/if}
                    </div>
                  </div>
                </div>

                <!-- Pimpinan Perguruan Tinggi -->
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col justify-between">
                  <div>
                    <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider flex items-center justify-between">
                      <div class="flex items-center gap-1">
                        <Award size={12} />
                        <span>Kepala / Pimpinan Kampus</span>
                      </div>
                      {#if ptDetail.nama_rektor}
                        <span class="text-[9px] bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 px-1.5 py-0.5 rounded font-mono font-bold">Terdata</span>
                      {/if}
                    </div>
                    <div class="font-bold text-slate-900 dark:text-white mt-1 {ptDetail.nama_rektor ? 'text-xs text-sky-700 dark:text-sky-300' : 'text-xs'}">
                      {ptDetail.nama_rektor || resolveLeaderTitle(ptDetail.nama_pt)}
                    </div>
                    <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                      {#if ptDetail.nama_rektor}
                        {resolveLeaderTitle(ptDetail.nama_pt)} resmi tercatat pada dokumen statuta & direktori institusi.
                      {:else}
                        Pimpinan eksekutif tertinggi pengesah naskah dinas dan ijazah sesuai statuta resmi institusi.
                      {/if}
                    </p>
                  </div>
                  {#if ptDetail.website}
                    <div class="mt-2 pt-1 border-t border-slate-200 dark:border-slate-800">
                      <a
                        href={ptDetail.website.startsWith('http') ? ptDetail.website : `https://${ptDetail.website}`}
                        target="_blank"
                        rel="noreferrer"
                        class="text-[11px] text-sky-600 dark:text-sky-400 font-semibold hover:underline flex items-center gap-1"
                      >
                        <span>Direktori Rektorat & Pimpinan</span>
                        <ExternalLink size={10} />
                      </a>
                    </div>
                  {/if}
                </div>

                <!-- Peta & Koordinat GPS -->
                <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3 border border-slate-200 dark:border-slate-700 shadow-2xs flex flex-col justify-between">
                  <div>
                    <div class="text-sky-600 dark:text-sky-400 text-[10px] font-mono font-semibold uppercase tracking-wider flex items-center gap-1">
                      <Compass size={12} />
                      <span>Koordinat Satelit & Peta</span>
                    </div>
                    <div class="font-mono font-bold text-slate-900 dark:text-white mt-1 text-xs">
                      {#if ptDetail.lintang_pt && ptDetail.bujur_pt}
                        {ptDetail.lintang_pt}, {ptDetail.bujur_pt}
                      {:else}
                        Koordinat GPS dalam verifikasi
                      {/if}
                    </div>
                    <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                      Geolokasi resmi kampus terdaftar pada basis data geospasial Kemdiktisaintek.
                    </p>
                  </div>
                  {#if ptDetail.lintang_pt && ptDetail.bujur_pt}
                    <div class="mt-2 pt-1 border-t border-slate-200 dark:border-slate-800">
                      <a
                        href={`https://www.google.com/maps?q=${ptDetail.lintang_pt},${ptDetail.bujur_pt}`}
                        target="_blank"
                        rel="noreferrer"
                        class="text-[11px] text-sky-600 dark:text-sky-400 font-semibold hover:underline flex items-center gap-1"
                      >
                        <span>Buka di Google Maps</span>
                        <ExternalLink size={10} />
                      </a>
                    </div>
                  {/if}
                </div>
              </div>
            </div>

            <!-- Media Sosial, Kontak Tambahan Web & Ringkasan Wikipedia -->
            {#if (ptDetail.social_media && Object.keys(ptDetail.social_media).length > 0) || (ptDetail.website_emails && ptDetail.website_emails.length > 0) || ptDetail.wiki_ringkasan || ptDetail.semboyan}
              <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 flex flex-col gap-3 shadow-xs">
                <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                  <div class="flex items-center gap-2">
                    <Globe size={16} class="text-sky-600 dark:text-sky-400" />
                    <h3 class="font-bold text-sm text-slate-900 dark:text-white">Konektivitas Web, Media Sosial & Ensiklopedia</h3>
                  </div>
                  {#if ptDetail.wiki_url}
                    <a
                      href={ptDetail.wiki_url}
                      target="_blank"
                      rel="noreferrer"
                      class="text-[11px] font-semibold text-sky-600 dark:text-sky-400 hover:underline inline-flex items-center gap-1"
                    >
                      <span>Artikel Wikipedia</span>
                      <ExternalLink size={11} />
                    </a>
                  {/if}
                </div>

                {#if ptDetail.semboyan}
                  <div class="px-3 py-1.5 rounded-lg bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 text-xs font-medium text-sky-900 dark:text-sky-200">
                    <span class="font-bold font-mono text-[10px] uppercase text-sky-600 dark:text-sky-400 mr-1.5">Semboyan:</span>
                    "{ptDetail.semboyan}"
                  </div>
                {/if}

                {#if ptDetail.wiki_ringkasan}
                  <div class="p-3 rounded-xl bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 leading-relaxed italic">
                    "{ptDetail.wiki_ringkasan}"
                  </div>
                {/if}

                <div class="flex flex-wrap items-center gap-2 pt-0.5">
                  {#if ptDetail.social_media?.instagram}
                    <a href={ptDetail.social_media.instagram} target="_blank" rel="noreferrer" class="px-2.5 py-1 rounded-lg bg-pink-50 dark:bg-pink-950/60 border border-pink-200 dark:border-pink-800 text-pink-700 dark:text-pink-300 text-xs font-semibold hover:bg-pink-100 dark:hover:bg-pink-900/60 transition inline-flex items-center gap-1">
                      <span>Instagram</span>
                      <ExternalLink size={10} />
                    </a>
                  {/if}
                  {#if ptDetail.social_media?.youtube}
                    <a href={ptDetail.social_media.youtube} target="_blank" rel="noreferrer" class="px-2.5 py-1 rounded-lg bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs font-semibold hover:bg-red-100 dark:hover:bg-red-900/60 transition inline-flex items-center gap-1">
                      <span>YouTube</span>
                      <ExternalLink size={10} />
                    </a>
                  {/if}
                  {#if ptDetail.social_media?.linkedin}
                    <a href={ptDetail.social_media.linkedin} target="_blank" rel="noreferrer" class="px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-semibold hover:bg-blue-100 dark:hover:bg-blue-900/60 transition inline-flex items-center gap-1">
                      <span>LinkedIn</span>
                      <ExternalLink size={10} />
                    </a>
                  {/if}
                  {#if ptDetail.social_media?.twitter}
                    <a href={ptDetail.social_media.twitter} target="_blank" rel="noreferrer" class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold hover:bg-slate-200 dark:hover:bg-slate-800 transition inline-flex items-center gap-1">
                      <span>Twitter / X</span>
                      <ExternalLink size={10} />
                    </a>
                  {/if}
                  {#if ptDetail.website_emails && ptDetail.website_emails.length > 0}
                    {#each ptDetail.website_emails as we}
                      <a href={`mailto:${we}`} class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono font-medium hover:text-sky-600 transition inline-flex items-center gap-1">
                        <Mail size={11} class="text-sky-600" />
                        <span>{we}</span>
                      </a>
                    {/each}
                  {/if}
                </div>
              </div>
            {/if}

            <!-- Rasio Dosen:Mahasiswa & Masa Studi per Jenjang -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Rasio Box -->
              <div class="rounded-2xl border border-sky-200 dark:border-sky-500/40 bg-sky-50/80 dark:bg-sky-950/30 p-4 flex flex-col justify-between shadow-xs">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-bold text-sky-900 dark:text-sky-200 flex items-center gap-1.5">
                    <BarChart3 size={15} class="text-sky-600 dark:text-sky-400" />
                    Rasio Dosen : Mahasiswa
                  </span>
                  {#if ptDetail.rasio?.semester}
                    <span class="text-[11px] font-mono text-sky-700 dark:text-sky-300 font-semibold">Semester {formatSemesterName(ptDetail.rasio.semester)}</span>
                  {/if}
                </div>
                <div class="grid grid-cols-3 gap-2 text-center pt-2">
                  <div class="bg-white dark:bg-[#0f172a] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase">Rasio Aktif</div>
                    <div class="text-base font-bold text-sky-700 dark:text-sky-300 mt-0.5">{ptDetail.rasio?.rasio || '1:25'}</div>
                  </div>
                  <div class="bg-white dark:bg-[#0f172a] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase">Dosen</div>
                    <div class="text-base font-bold text-slate-900 dark:text-white mt-0.5">{ptDetail.rasio?.dosen || '-'}</div>
                  </div>
                  <div class="bg-white dark:bg-[#0f172a] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700">
                    <div class="text-[10px] text-slate-500 dark:text-slate-400 font-mono uppercase">Mahasiswa</div>
                    <div class="text-base font-bold text-slate-900 dark:text-white mt-0.5">{ptDetail.rasio?.mahasiswa || '-'}</div>
                  </div>
                </div>
              </div>

              <!-- Masa Studi Box -->
              <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 flex flex-col justify-between shadow-xs">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <GraduationCap size={15} class="text-sky-600 dark:text-sky-400" />
                    Rata-rata Masa Studi
                  </span>
                  <span class="text-[11px] text-slate-500 dark:text-slate-400 font-mono font-medium">Berdasarkan Jenjang</span>
                </div>
                {#if ptDetail.waktu_studi && ptDetail.waktu_studi.length > 0}
                  <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2">
                    {#each ptDetail.waktu_studi as ws}
                      <div class="bg-slate-50 dark:bg-[#0f172a] p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-center">
                        <div class="text-[10px] text-sky-600 dark:text-sky-400 font-mono font-bold uppercase">{ws.jenjang}</div>
                        <div class="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{ws.mean_masa_studi} tahun</div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
                    Informasi rata-rata masa studi belum tercatat di PDDIKTI.
                  </div>
                {/if}
              </div>
            </div>

            <!-- PROGRAM STUDI TABLE PANEL -->
            <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 sm:p-5 flex flex-col gap-3.5 shadow-sm dark:shadow-xl">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-700 pb-3">
                <div>
                  <div class="flex items-center gap-2">
                    <BookOpen size={16} class="text-sky-600 dark:text-sky-400" />
                    <h3 class="font-bold text-base text-slate-900 dark:text-white">Program Studi</h3>
                    <span class="text-[11px] font-mono px-2 py-0.5 rounded-md bg-sky-50 dark:bg-sky-950 border border-sky-300 dark:border-sky-700 text-sky-700 dark:text-sky-300 font-bold">
                      {filteredProdiList.length} Prodi
                    </span>
                  </div>
                  <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Daftar lengkap program studi, akreditasi, rasio pendidik, dan jumlah mahasiswa {ptDetail.prodi_semester ? `(${formatSemesterName(ptDetail.prodi_semester)})` : ''}.
                  </p>
                </div>

                <!-- Prodi Search & Page Size Select -->
                <div class="flex items-center gap-2">
                  <div class="relative w-full sm:w-64">
                    <Search size={13} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      bind:value={prodiSearch}
                      placeholder="Cari prodi atau kode..."
                      class="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-50 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                  <div class="flex items-center gap-1 text-slate-600 dark:text-slate-300 text-xs flex-shrink-0">
                    <span class="hidden sm:inline text-[11px]">Tampilkan:</span>
                    <select
                      bind:value={prodiPageSize}
                      class="px-2 py-1.5 rounded-lg bg-slate-50 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-sky-500 font-semibold"
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Responsive Table Container -->
              <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
                <table class="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr class="bg-slate-100 dark:bg-[#0f172a] text-slate-700 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 text-[11px]">
                      <th class="p-2.5 font-mono">Kode</th>
                      <th class="p-2.5">Program Studi</th>
                      <th class="p-2.5 text-center">Jenjang</th>
                      <th class="p-2.5 text-center">Status</th>
                      <th class="p-2.5 text-center">Akreditasi</th>
                      <th class="p-2.5 text-center" title="Dosen Penghitung Rasio">Dosen Ajar</th>
                      <th class="p-2.5 text-center" title="Pendidik: Tetap / Tidak Tetap (Total)">Pendidik (NIDN/K)</th>
                      <th class="p-2.5 text-center">Mahasiswa</th>
                      <th class="p-2.5 text-center">Rasio</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-200 dark:divide-slate-800 bg-white dark:bg-[#1e293b]">
                    {#if paginatedProdiList.length === 0}
                      <tr>
                        <td colspan="9" class="p-6 text-center text-slate-500 dark:text-slate-400 text-xs">
                          Tidak ada program studi yang cocok dengan kata kunci pencarian.
                        </td>
                      </tr>
                    {:else}
                      {#each paginatedProdiList as p}
                        <tr class="hover:bg-slate-50 dark:hover:bg-[#25334d] transition-colors">
                          <td class="p-2.5 font-mono text-[11px] font-semibold text-sky-700 dark:text-sky-300">{p.kode_prodi}</td>
                          <td class="p-2.5 font-bold text-slate-900 dark:text-white">{p.nama_prodi}</td>
                          <td class="p-2.5 text-center font-mono font-semibold text-slate-700 dark:text-slate-300">{p.jenjang_prodi || '-'}</td>
                          <td class="p-2.5 text-center">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold {p.status_prodi === 'Aktif' ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700' : 'bg-rose-50 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-700'}">
                              {p.status_prodi || 'Aktif'}
                            </span>
                          </td>
                          <td class="p-2.5 text-center font-semibold text-slate-800 dark:text-slate-200">
                            {#if p.akreditasi}
                              <span class="px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950 border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 text-[10px] font-bold">
                                {p.akreditasi}
                              </span>
                            {:else}
                              <span class="text-slate-400">-</span>
                            {/if}
                          </td>
                          <td class="p-2.5 text-center font-mono font-semibold text-slate-800 dark:text-slate-200">{p.jumlah_dosen_ajar ?? 0}</td>
                          <td class="p-2.5 text-center font-mono text-[11px] text-slate-700 dark:text-slate-300">
                            {p.jumlah_dosen_nidn ?? 0} / {p.jumlah_dosen_nidk ?? 0} <span class="font-bold text-slate-900 dark:text-white">({p.jumlah_dosen ?? 0})</span>
                          </td>
                          <td class="p-2.5 text-center font-mono font-bold text-slate-900 dark:text-white">{p.jumlah_mahasiswa ?? 0}</td>
                          <td class="p-2.5 text-center font-mono font-bold text-sky-700 dark:text-sky-300">{p.rasio || '-'}</td>
                        </tr>
                      {/each}
                    {/if}
                  </tbody>
                </table>
              </div>

              <!-- Prodi Pagination Controls -->
              {#if prodiTotalPages > 1}
                <div class="flex items-center justify-between pt-1 text-xs text-slate-700 dark:text-slate-300">
                  <span class="font-mono text-[11px] font-semibold">
                    Halaman {prodiPage} dari {prodiTotalPages}
                  </span>
                  <div class="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={prodiPage <= 1}
                      onclick={() => prodiPage--}
                      class="px-3 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 hover:border-sky-500 disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition font-semibold"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      disabled={prodiPage >= prodiTotalPages}
                      onclick={() => prodiPage++}
                      class="px-3 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-300 dark:border-slate-600 hover:border-sky-500 disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition font-semibold"
                    >
                      Next
                    </button>
                  </div>
                </div>
              {/if}
            </div>

            <!-- Fasilitas / Sarpras & Riwayat Kampus Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Fasilitas Kampus -->
              <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 flex flex-col gap-3 shadow-xs">
                <div class="flex items-center gap-2">
                  <Building2 size={16} class="text-sky-600 dark:text-sky-400" />
                  <h3 class="font-bold text-sm text-slate-900 dark:text-white">Fasilitas & Sarana Prasarana</h3>
                </div>
                {#if ptDetail.sarpras && ptDetail.sarpras.length > 0}
                  <div class="flex flex-wrap gap-1.5">
                    {#each ptDetail.sarpras as item}
                      <span class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-1">
                        <Check size={11} class="text-emerald-500" />
                        <span>{item.file_name.replace(/\.(jpg|png|jpeg|webp)$/i, '')}</span>
                      </span>
                    {/each}
                  </div>
                {:else}
                  <div class="text-xs text-slate-500 dark:text-slate-400">
                    Tidak ada data fasilitas atau sarpras yang diunggah.
                  </div>
                {/if}
              </div>

              <!-- Riwayat Perguruan Tinggi -->
              <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b] p-4 flex flex-col gap-3 shadow-xs">
                <div class="flex items-center gap-2">
                  <History size={16} class="text-sky-600 dark:text-sky-400" />
                  <h3 class="font-bold text-sm text-slate-900 dark:text-white">Riwayat Perguruan Tinggi</h3>
                </div>
                {#if ptDetail.name_histories && ptDetail.name_histories.length > 0}
                  <div class="flex flex-col gap-2">
                    {#each ptDetail.name_histories as hist}
                      <div class="p-2.5 rounded-xl bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 text-xs">
                        <div class="font-bold text-slate-900 dark:text-white">{hist.nama_pt_sebelumnya}</div>
                        <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Tahun: {hist.tahun || '-'} • SK: {hist.sk_perubahan || '-'}</div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="text-xs text-slate-500 dark:text-slate-400">
                    Tidak ada data riwayat perubahan perguruan tinggi.
                  </div>
                {/if}
              </div>
            </div>

            <!-- Official Portal Verification Link -->
            {#if ptDetail.verify_url}
              <div class="rounded-xl bg-slate-50 dark:bg-[#1e293b] p-3.5 border border-slate-200 dark:border-slate-700 shadow-2xs flex items-center justify-between">
                <div>
                  <div class="text-sky-600 dark:text-sky-400 text-[11px] font-mono font-semibold uppercase tracking-wider">Verifikasi Kampus PDDIKTI</div>
                  <div class="text-slate-600 dark:text-slate-300 text-xs mt-0.5">Tervalidasi langsung pada direktori Perguruan Tinggi Kemdiktisaintek RI.</div>
                </div>
                <a
                  href={ptDetail.verify_url}
                  target="_blank"
                  rel="noreferrer"
                  class="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-xs"
                >
                  <span>Buka Portal Resmi</span>
                  <ExternalLink size={13} />
                </a>
              </div>
            {/if}
          </div>

        {:else}
          <div class="rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-[#1e293b]/70 p-12 text-center text-slate-500 dark:text-slate-200 text-xs font-medium shadow-sm">
            Pilih salah satu hasil dari daftar di sebelah kiri untuk melihat rincian lengkap profil atau mengunduh berkas resmi.
          </div>
        {/if}
      </div>
    </div>
    {/if}
  </main>

  <!-- Fullscreen Zoom Modal (For Mahasiswa Document Preview) -->
  {#if showFullscreenModal && inlinePreviewUrl}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 dark:bg-black/90 backdrop-blur-sm p-4">
      <div class="bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 rounded-2xl max-w-4xl w-full max-h-[94vh] flex flex-col shadow-2xl overflow-hidden">
        <div class="px-5 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] flex items-center justify-between">
          <div class="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
            <Eye size={16} class="text-sky-600 dark:text-sky-400" />
            <span>Pratinjau Dokumen: {activeTemplate.toUpperCase()}</span>
          </div>
          <div class="flex items-center gap-3">
            <button
              type="button"
              onclick={() => handleDownload('pdf')}
              class="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition cursor-pointer flex items-center gap-1.5 shadow-xs"
            >
              <Download size={13} />
              <span>Unduh PDF</span>
            </button>
            <button
              type="button"
              onclick={() => showFullscreenModal = false}
              class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div class="flex-grow overflow-y-auto p-4 sm:p-6 bg-slate-100 dark:bg-[#0f172a] flex items-center justify-center">
          <div class="max-w-2xl w-full bg-white rounded-lg shadow-2xl overflow-hidden border-2 border-slate-300 dark:border-slate-500">
            <img
              src={inlinePreviewUrl}
              alt="Pratinjau Dokumen Layar Penuh"
              class="w-full h-auto block"
            />
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Tentang & FAQ Modal (Strict Anti-Slop, Clean & Informative) -->
  {#if showAboutModal}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 dark:bg-black/80 backdrop-blur-sm p-4">
      <div class="bg-white dark:bg-[#1e293b] border-2 border-slate-200 dark:border-slate-600 rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <!-- Modal Header -->
        <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-600 dark:text-sky-400">
              <Info size={17} />
            </div>
            <div>
              <h3 class="text-base font-bold text-slate-900 dark:text-white">Tentang CivitasID & Panduan</h3>
              <p class="text-[11px] text-slate-500 dark:text-slate-300 font-mono">Platform Eksplorasi Data Terbuka PDDIKTI Kemdiktisaintek RI</p>
            </div>
          </div>
          <button
            type="button"
            onclick={() => showAboutModal = false}
            class="text-slate-400 hover:text-slate-700 dark:hover:text-white transition cursor-pointer p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X size={20} />
          </button>
        </div>

        <!-- Modal Content Scrollable Body -->
        <div class="overflow-y-auto p-5 sm:p-6 flex flex-col gap-5 text-xs text-slate-700 dark:text-slate-200">
          <!-- 3 Architectural Pillars -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700">
              <div class="flex items-center gap-2 text-sky-600 dark:text-sky-400 font-bold mb-1">
                <Server size={15} />
                <span>Koneksi Langsung</span>
              </div>
              <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
                Terhubung real-time ke pangkalan data resmi PDDIKTI via browser proxy headless Playwright tanpa bot intercept.
              </p>
            </div>

            <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700">
              <div class="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold mb-1">
                <Globe size={15} />
                <span>Kop & Stempel Dinamis</span>
              </div>
              <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
                Stempel kurva vektor SVG dan lambang heraldik dibentuk otomatis sesuai perguruan tinggi asal tanpa template statis.
              </p>
            </div>

            <div class="rounded-xl bg-slate-50 dark:bg-[#0f172a] p-3.5 border border-slate-200 dark:border-slate-700">
              <div class="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-bold mb-1">
                <Shield size={15} />
                <span>Zero-Storage Policy</span>
              </div>
              <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
                Server tidak menyimpan basis data pribadi mahasiswa atau dosen. Seluruh pemrosesan berjalan in-memory.
              </p>
            </div>
          </div>

          <!-- Peta Ekosistem Sumber Data -->
          <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] p-4 flex flex-col gap-3">
            <div class="flex items-center gap-2">
              <BookOpen size={16} class="text-sky-600 dark:text-sky-400" />
              <h4 class="font-bold text-xs text-slate-900 dark:text-white uppercase tracking-wider font-mono">
                Peta Sumber Data & Ekosistem Terintegrasi
              </h4>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-sky-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">PDDIKTI Kemdiktisaintek RI</strong>
                  <span class="text-slate-500 dark:text-slate-400">Data induk mahasiswa, dosen, perguruan tinggi, riwayat studi & mengajar.</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-indigo-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">SINTA Kemdiktisaintek RI</strong>
                  <span class="text-slate-500 dark:text-slate-400">Profil publikasi riset, SINTA Score 3Yr & Overall, Scopus H-Index, dan foto dosen.</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-blue-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">Google Scholar & Repositori</strong>
                  <span class="text-slate-500 dark:text-slate-400">Indeks sitasi artikel ilmiah, kutipan sitasi, dan tautan profil author internasional.</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">Wikipedia & Statuta Institusi</strong>
                  <span class="text-slate-500 dark:text-slate-400">Nama pimpinan resmi (Rektor/Direktur/Ketua), bentuk perguruan tinggi, & semboyan.</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-pink-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">Portal Web Resmi Kampus</strong>
                  <span class="text-slate-500 dark:text-slate-400">Media sosial resmi (Instagram, YouTube, LinkedIn, X) dan kontak email domain kampus.</span>
                </div>
              </div>
              <div class="p-2.5 rounded-lg bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-500 mt-1 flex-shrink-0"></span>
                <div>
                  <strong class="text-slate-900 dark:text-white block">RAMA & SIVIL Kemdiktisaintek</strong>
                  <span class="text-slate-500 dark:text-slate-400">Repositori tugas akhir/skripsi dan verifikasi ijazah elektronik berbasis NIN.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- FAQ Accordion -->
          <div class="flex flex-col gap-2 pt-2">
            <div class="text-xs font-mono font-bold text-sky-600 dark:text-sky-400 uppercase tracking-wider mb-1">
              Pertanyaan yang Sering Diajukan (FAQ)
            </div>

            <div class="flex flex-col gap-2">
              {#each FAQ_ITEMS as faq, idx}
                <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] overflow-hidden transition">
                  <button
                    type="button"
                    onclick={() => activeFaqIndex = activeFaqIndex === idx ? null : idx}
                    class="w-full px-4 py-3 text-left flex items-center justify-between gap-3 text-xs font-bold text-slate-900 dark:text-white hover:text-sky-600 dark:hover:text-sky-300 transition cursor-pointer"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown size={15} class="text-slate-400 transition-transform duration-200 flex-shrink-0 {activeFaqIndex === idx ? 'rotate-180 text-sky-600 dark:text-sky-400' : ''}" />
                  </button>
                  {#if activeFaqIndex === idx}
                    <div class="px-4 pb-3.5 pt-0.5 text-slate-600 dark:text-slate-300 text-xs leading-relaxed border-t border-slate-200 dark:border-slate-800/80 font-normal">
                      {faq.a}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </div>

          <!-- Telegram Bot Integration Info -->
          <div class="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-4 flex flex-col gap-2 text-xs">
            <div class="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
              <Code2 size={16} class="text-sky-600 dark:text-sky-400" />
              <span>Integrasi Bot Telegram Mandiri</span>
            </div>
            <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
              CivitasID dilengkapi backend bot Telegram bawaan (berbasis <code class="text-sky-600 dark:text-sky-300 font-mono">aiogram 3</code>).
              Untuk mengaktifkan: atur <code class="text-sky-600 dark:text-sky-300 font-mono">ENABLE_TELEGRAM_BOT=true</code> dan isi <code class="text-sky-600 dark:text-sky-300 font-mono">TELEGRAM_BOT_TOKEN</code> di file <code class="text-sky-600 dark:text-sky-300 font-mono">.env</code> backend.
            </p>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="px-5 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#0f172a] flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span class="font-mono text-[11px]">CivitasID v1.3.0 • Open Source (MIT)</span>
          <button
            type="button"
            onclick={() => showAboutModal = false}
            class="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold transition cursor-pointer"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Clean Footer -->
  <footer class="border-t border-slate-200 dark:border-slate-800 py-6 mt-12 bg-white dark:bg-[#0f172a] text-xs text-slate-500 dark:text-slate-400">
    <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
      <div class="flex items-center gap-3">
        <span>CivitasID — Platform eksplorasi data terbuka PDDIKTI Kemdiktisaintek RI.</span>
        <button
          type="button"
          onclick={() => showAboutModal = true}
          class="text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300 underline font-medium cursor-pointer"
        >
          Tentang & FAQ
        </button>
      </div>
      <div>
        <span>Pratinjau digital dinamis untuk keperluan administratif independen.</span>
      </div>
    </div>
  </footer>
</div>
