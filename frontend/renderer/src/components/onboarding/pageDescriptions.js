/**
 * Shared page descriptions used by both SpotlightTour and ZippyMenu.
 * Keyed by nav-page id (matches NAV_ITEMS ids and TOUR_STEPS targets).
 */

export const PAGE_DESCRIPTIONS = {
  dashboard: {
    expression: 'pointing',
    message:
      'This is your command center! Upload a .zip of your code repo here to get started. Once uploaded, I\'ll analyze it and pull out the good stuff \u2014 languages, frameworks, and skills.',
  },
  projects: {
    expression: 'excited',
    message:
      'All your uploaded projects show up here. Click on any project to edit its name, add a description, or re-run the analysis. You can also rank your projects by importance.',
  },
  analyses: {
    expression: 'happy',
    message:
      'This is where the magic happens! See exactly what was detected in your code \u2014 languages used, design patterns, complexity metrics. You can edit or tweak any analysis result.',
  },
  skills: {
    expression: 'pointing',
    message:
      'Your skill inventory! Every technology and framework detected across all your projects gets collected here. These feed directly into your resume and portfolio.',
  },
  experience: {
    expression: 'wave',
    message:
      'Add your work history \u2014 jobs, internships, co-ops. Include bullet points about what you did. These show up on your generated resume alongside your projects.',
  },
  education: {
    expression: 'excited',
    message:
      "Add your degrees, certifications, and coursework. Include your GPA if you'd like. This section goes right onto your resume.",
  },
  profile: {
    expression: 'happy',
    message:
      "Fill this in first! Your name, email, phone, LinkedIn, and GitHub go here. Without a profile, resume PDF generation won't work.",
  },
  portfolio: {
    expression: 'pointing',
    message:
      'Generate a portfolio website that showcases your top projects with descriptions, skills, and thumbnails. Perfect for sharing with recruiters.',
  },
  resumes: {
    expression: 'excited',
    message:
      'The grand finale! Pick a template, select your projects, and generate a polished PDF resume. AI can even write your bullet points if you enable it in Consents.',
  },
  consents: {
    expression: 'wave',
    message:
      'Control your privacy here. Toggle AI features on or off, manage which external services can access your data, and set file ignore patterns.',
  },
}

export const DEFAULT_DESCRIPTION = {
  expression: 'happy',
  message:
    "I'm Zippy, your guide to Zip2Job! Click 'Start Tour' to learn about every page, or ask me about this one.",
}
