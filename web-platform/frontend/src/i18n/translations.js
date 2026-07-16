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
    'ctrl.toFr': 'Switch to French',
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

  fr: {
    // App shell
    'brand.title': 'Cockpit analytique',
    'brand.subtitle': 'ANALYSE ÉDU · V1.1',
    'header.appTitle':
      "Analyse des performances étudiantes pilotée par l'IA et aide à la décision pédagogique",
    'header.appSubtitle': "COMP8567 · Équipe 7 · Plateforme d'analyse pédagogique",
    'system.online': 'Système en ligne',
    'system.inference': 'Inférence :',
    'system.sampleData': "Mode données d'exemple",

    // Navigation
    'nav.dashboard': 'Tableau de bord',
    'nav.courses': 'Cours',
    'nav.sections': 'Sections',
    'nav.comparisons': 'Comparaisons',
    'nav.cohortInsights': 'Analyses de cohorte',
    'nav.reports': 'Rapports',

    // User menu
    'user.profile': 'Profil',
    'user.signOut': 'Se déconnecter',
    'user.administrator': 'Administrateur',
    'user.instructor': 'Enseignant',

    // Controls
    'ctrl.toLight': 'Passer en mode jour',
    'ctrl.toDark': 'Passer en mode nuit',
    'ctrl.toFr': 'Passer en français',
    'ctrl.toEn': 'Passer en anglais',
    'ctrl.langShort': 'FR',

    // Risk
    'risk.HIGH': 'Élevé',
    'risk.MEDIUM': 'Moyen',
    'risk.LOW': 'Faible',

    // Common
    'common.recalculate': 'Recalculer',
    'common.overview': "Vue d'ensemble",
    'common.prediction': 'Prédiction',
    'common.import': 'Importer',
    'common.createCourse': 'Créer un cours',
    'common.section': 'Section',
    'common.course': 'Cours',

    // Dashboard
    'dash.welcome': 'Centre de commande · Bienvenue, {name}',
    'dash.subtitle':
      "Vue d'ensemble de l'état pédagogique et des alertes de risque clés (données d'exemple)",
    'dash.kpi.courses': 'Mes cours',
    'dash.kpi.sections': 'Sections',
    'dash.kpi.students': 'Étudiants',
    'dash.kpi.highRisk': 'Étudiants à haut risque',
    'dash.kpi.needsAttention': 'À surveiller',
    'dash.noSections':
      "Aucune section pour l'instant. Créez un cours et une section pour commencer l'analyse.",
    'dash.weeklyTrend': 'Tendance hebdomadaire de la moyenne',
    'dash.lastCalculated': 'Dernier calcul : {time}',
    'dash.average': 'Moyenne',
    'dash.riskDistribution': 'Répartition des risques',
    'dash.scoreDistribution': 'Répartition des notes',
    'dash.studentsSeries': 'Étudiants',
    'dash.watchlist': 'Liste de surveillance à haut risque',
    'dash.watchlistSubtitle': 'Triés par probabilité de risque — cliquez pour voir un étudiant',
    'dash.noHighRisk': 'Aucun étudiant à haut risque',
    'dash.riskProbability': 'Probabilité de risque',
    'dash.recalcTriggered': 'Recalcul déclenché',
    'dash.loadFailed': 'Échec du chargement du tableau de bord',
    'dash.overviewFailed': 'Échec du chargement de la vue de section',
    'dash.opFailed': "Échec de l'opération",

    // Auth
    'auth.appName': 'Analyse des performances étudiantes et aide à la décision',
    'auth.intro':
      "Transformez quiz, devoirs, présence et activité d'apprentissage en informations pédagogiques claires, traçables et exploitables.",
    'auth.feature1': "Vue d'ensemble de classe · instantanés multidimensionnels",
    'auth.feature2': 'Prédiction du risque par IA · explicabilité SHAP',
    'auth.feature3': 'Tendance / distribution / comparaison de cohortes',
    'auth.welcomeBack': 'Bon retour 👋',
    'auth.signInHint': 'Connectez-vous pour accéder au cockpit',
    'auth.username': "Nom d'utilisateur",
    'auth.password': 'Mot de passe',
    'auth.usernameRequired': "Veuillez saisir votre nom d'utilisateur",
    'auth.passwordRequired': 'Veuillez saisir votre mot de passe',
    'auth.signIn': 'Se connecter',
    'auth.noAccount': 'Pas encore de compte ?',
    'auth.createAccount': 'Créer un compte',
    'auth.signedIn': 'Connecté',
    'auth.loginFailed': 'Échec de la connexion',
    // Register
    'auth.registerTitle': 'Créer un compte',
    'auth.registerHint': "Le premier utilisateur peut s'inscrire comme enseignant / admin",
    'auth.fullName': 'Nom complet',
    'auth.email': 'E-mail',
    'auth.emailInvalid': 'Veuillez saisir un e-mail valide',
    'auth.role': 'Rôle',
    'auth.usernameRequired2': "Veuillez saisir un nom d'utilisateur",
    'auth.passwordMin': 'Au moins 6 caractères',
    'auth.signUpSignIn': "S'inscrire et se connecter",
    'auth.registeredSignedIn': 'Compte créé et connecté',
    'auth.alreadyHave': 'Vous avez déjà un compte ?',
    'auth.backSignIn': 'Retour à la connexion',
    'auth.registerFailed': "Échec de l'inscription",
  },
};
