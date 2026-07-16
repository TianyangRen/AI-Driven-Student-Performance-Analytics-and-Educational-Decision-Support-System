/**
 * UI translation dictionary. Keys are dot-namespaced. Missing keys fall back
 * to English, then to the raw key, so partially-translated pages keep working.
 *
 * To localize another page: add keys here and replace hardcoded strings with
 * `t('your.key')` from `useI18n()`.
 */
export const translations = {
  en: {
    // App shell
    'brand.title': 'Analytics Cockpit',
    'brand.subtitle': 'EDU ANALYTICS · V1.1',
    'header.appTitle': 'AI-Driven Student Performance Analytics & Educational Decision Support',
    'header.appSubtitle': 'COMP8567 · Team 7 · Teaching analytics platform',
    'system.online': 'System online',
    'system.inference': 'Inference:',
    'system.sampleData': 'Sample data mode',

    // Navigation
    'nav.dashboard': 'Dashboard',
    'nav.courses': 'Courses',
    'nav.sections': 'Sections',
    'nav.comparisons': 'Comparisons',
    'nav.cohortInsights': 'Cohort Insights',
    'nav.reports': 'Reports',

    // User menu
    'user.profile': 'Profile',
    'user.signOut': 'Sign out',
    'user.administrator': 'Administrator',
    'user.instructor': 'Instructor',

    // Controls
    'ctrl.toLight': 'Switch to day mode',
    'ctrl.toDark': 'Switch to night mode',
    'ctrl.toZh': 'Switch to Chinese',
    'ctrl.toEn': 'Switch to English',
    'ctrl.langShort': 'EN',

    // Risk
    'risk.HIGH': 'High',
    'risk.MEDIUM': 'Medium',
    'risk.LOW': 'Low',

    // Common
    'common.recalculate': 'Recalculate',
    'common.overview': 'Overview',
    'common.prediction': 'Prediction',
    'common.import': 'Import',
    'common.createCourse': 'Create a course',
    'common.section': 'Section',
    'common.course': 'Course',

    // Dashboard
    'dash.welcome': 'Command Center · Welcome, {name}',
    'dash.subtitle': 'Global teaching status and key risk alerts at a glance (sample data)',
    'dash.kpi.courses': 'My courses',
    'dash.kpi.sections': 'Sections',
    'dash.kpi.students': 'Students',
    'dash.kpi.highRisk': 'High-risk students',
    'dash.kpi.needsAttention': 'Needs attention',
    'dash.noSections': 'No sections yet. Create a course and section to start analyzing.',
    'dash.weeklyTrend': 'Weekly average score trend',
    'dash.lastCalculated': 'Last calculated: {time}',
    'dash.average': 'Average',
    'dash.riskDistribution': 'Risk distribution',
    'dash.scoreDistribution': 'Score distribution',
    'dash.studentsSeries': 'Students',
    'dash.watchlist': 'High-risk watchlist',
    'dash.watchlistSubtitle': 'Sorted by risk probability — click to view a student',
    'dash.noHighRisk': 'No high-risk students',
    'dash.riskProbability': 'Risk probability',
    'dash.recalcTriggered': 'Recalculation triggered',
    'dash.loadFailed': 'Failed to load dashboard',
    'dash.overviewFailed': 'Failed to load section overview',
    'dash.opFailed': 'Operation failed',

    // Auth
    'auth.appName': 'Student Performance Analytics & Decision Support',
    'auth.intro':
      'Turn quizzes, assignments, attendance and learning activity into clear, traceable and actionable teaching insights.',
    'auth.feature1': 'Class overview · multi-dimensional snapshots',
    'auth.feature2': 'AI risk prediction · SHAP explainability',
    'auth.feature3': 'Trend / distribution / cohort comparison',
    'auth.welcomeBack': 'Welcome back 👋',
    'auth.signInHint': 'Sign in to enter the cockpit',
    'auth.username': 'Username',
    'auth.password': 'Password',
    'auth.usernameRequired': 'Please enter your username',
    'auth.passwordRequired': 'Please enter your password',
    'auth.signIn': 'Sign in',
    'auth.noAccount': 'No account yet?',
    'auth.createAccount': 'Create account',
    'auth.signedIn': 'Signed in',
    'auth.loginFailed': 'Login failed',
    // Register
    'auth.registerTitle': 'Create account',
    'auth.registerHint': 'The first user can register as instructor / admin',
    'auth.fullName': 'Full name',
    'auth.email': 'Email',
    'auth.emailInvalid': 'Please enter a valid email',
    'auth.role': 'Role',
    'auth.usernameRequired2': 'Please enter a username',
    'auth.passwordMin': 'At least 6 characters',
    'auth.signUpSignIn': 'Sign up & sign in',
    'auth.registeredSignedIn': 'Account created and signed in',
    'auth.alreadyHave': 'Already have an account?',
    'auth.backSignIn': 'Back to sign in',
    'auth.registerFailed': 'Registration failed',
  },

  zh: {
    // App shell
    'brand.title': '分析驾驶舱',
    'brand.subtitle': '教育分析 · V1.1',
    'header.appTitle': 'AI 驱动的学生表现分析与教育决策支持系统',
    'header.appSubtitle': 'COMP8567 · 第 7 组 · 教学分析平台',
    'system.online': '系统在线',
    'system.inference': '推理引擎：',
    'system.sampleData': '示例数据模式',

    // Navigation
    'nav.dashboard': '仪表盘',
    'nav.courses': '课程',
    'nav.sections': '教学班',
    'nav.comparisons': '对比分析',
    'nav.cohortInsights': '群体洞察',
    'nav.reports': '报告',

    // User menu
    'user.profile': '个人资料',
    'user.signOut': '退出登录',
    'user.administrator': '管理员',
    'user.instructor': '教师',

    // Controls
    'ctrl.toLight': '切换到白天模式',
    'ctrl.toDark': '切换到夜间模式',
    'ctrl.toZh': '切换到中文',
    'ctrl.toEn': '切换到英文',
    'ctrl.langShort': '中',

    // Risk
    'risk.HIGH': '高',
    'risk.MEDIUM': '中',
    'risk.LOW': '低',

    // Common
    'common.recalculate': '重新计算',
    'common.overview': '概览',
    'common.prediction': '预测',
    'common.import': '导入',
    'common.createCourse': '创建课程',
    'common.section': '教学班',
    'common.course': '课程',

    // Dashboard
    'dash.welcome': '指挥中心 · 欢迎你，{name}',
    'dash.subtitle': '一览全局教学状态与关键风险预警（示例数据）',
    'dash.kpi.courses': '我的课程',
    'dash.kpi.sections': '教学班',
    'dash.kpi.students': '学生',
    'dash.kpi.highRisk': '高风险学生',
    'dash.kpi.needsAttention': '需要关注',
    'dash.noSections': '还没有教学班。请先创建课程和教学班，即可开始分析。',
    'dash.weeklyTrend': '每周平均分趋势',
    'dash.lastCalculated': '最近计算时间：{time}',
    'dash.average': '平均分',
    'dash.riskDistribution': '风险分布',
    'dash.scoreDistribution': '成绩分布',
    'dash.studentsSeries': '学生数',
    'dash.watchlist': '高风险关注名单',
    'dash.watchlistSubtitle': '按风险概率排序 —— 点击查看学生详情',
    'dash.noHighRisk': '暂无高风险学生',
    'dash.riskProbability': '风险概率',
    'dash.recalcTriggered': '已触发重新计算',
    'dash.loadFailed': '加载仪表盘失败',
    'dash.overviewFailed': '加载教学班概览失败',
    'dash.opFailed': '操作失败',

    // Auth
    'auth.appName': '学生表现分析与决策支持系统',
    'auth.intro': '把测验、作业、考勤与学习行为，转化为清晰、可追溯、可执行的教学洞察。',
    'auth.feature1': '课堂概览 · 多维度快照',
    'auth.feature2': 'AI 风险预测 · SHAP 可解释性',
    'auth.feature3': '趋势 / 分布 / 群体对比',
    'auth.welcomeBack': '欢迎回来 👋',
    'auth.signInHint': '登录以进入驾驶舱',
    'auth.username': '用户名',
    'auth.password': '密码',
    'auth.usernameRequired': '请输入用户名',
    'auth.passwordRequired': '请输入密码',
    'auth.signIn': '登录',
    'auth.noAccount': '还没有账号？',
    'auth.createAccount': '创建账号',
    'auth.signedIn': '登录成功',
    'auth.loginFailed': '登录失败',
    // Register
    'auth.registerTitle': '创建账号',
    'auth.registerHint': '第一个用户可注册为教师 / 管理员',
    'auth.fullName': '姓名',
    'auth.email': '邮箱',
    'auth.emailInvalid': '请输入有效的邮箱',
    'auth.role': '角色',
    'auth.usernameRequired2': '请输入用户名',
    'auth.passwordMin': '至少 6 个字符',
    'auth.signUpSignIn': '注册并登录',
    'auth.registeredSignedIn': '账号创建成功并已登录',
    'auth.alreadyHave': '已经有账号了？',
    'auth.backSignIn': '返回登录',
    'auth.registerFailed': '注册失败',
  },
};
