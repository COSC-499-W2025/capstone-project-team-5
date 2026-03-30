export const SETUP_STEPS = [
  {
    id: 'profile',
    page: 'profile',
    expression: 'pointing',
    message:
      "Let's start with your profile! Fill in at least your first and last name \u2014 they're required for your resume.",
    event: 'z2j:profile-saved',
    skippable: false,
    hasScrim: false,
    checkComplete: async (username) => {
      try {
        const profile = await window.api.getProfile(username)
        return !!(profile?.first_name && profile?.last_name)
      } catch {
        return false
      }
    },
  },
  {
    id: 'experience',
    page: 'experience',
    expression: 'wave',
    message:
      "Nice! Now let's add some work experience. This isn't required, but it really makes your resume shine!",
    event: 'z2j:experience-saved',
    skippable: true,
    hasScrim: false,
    checkComplete: async (username) => {
      try {
        const items = await window.api.getWorkExperiences(username)
        return Array.isArray(items) && items.length > 0
      } catch {
        return false
      }
    },
  },
  {
    id: 'education',
    page: 'education',
    expression: 'excited',
    message:
      "How about education? Same deal \u2014 optional but recommended for a polished resume.",
    event: 'z2j:education-saved',
    skippable: true,
    hasScrim: false,
    checkComplete: async (username) => {
      try {
        const items = await window.api.getEducations(username)
        return Array.isArray(items) && items.length > 0
      } catch {
        return false
      }
    },
  },
  {
    id: 'upload',
    page: 'dashboard',
    expression: 'pointing',
    message:
      "Now the fun part! Click 'Upload Project' and select a .zip of your code repo.",
    event: 'z2j:upload-complete',
    skippable: false,
    hasScrim: false,
    checkComplete: null,
  },
  {
    id: 'projects',
    page: 'projects',
    expression: 'excited',
    message:
      "Here's your project! Click on it and hit 'Analyze' to extract your role, skills, and resume bullets.",
    event: 'z2j:analysis-complete',
    skippable: false,
    hasScrim: false,
    checkComplete: null,
  },
  {
    id: 'resumes',
    page: 'resumes',
    expression: 'pointing',
    message:
      "Last step! Click '+ Add Resume Project Entry' to build a resume entry from your project.",
    event: 'z2j:resume-saved',
    skippable: false,
    hasScrim: false,
    checkComplete: async (username) => {
      try {
        const items = await window.api.getResumes(username)
        return Array.isArray(items) && items.length > 0
      } catch {
        return false
      }
    },
  },
  {
    id: 'done',
    page: 'resumes',
    expression: 'thumbsup',
    message:
      "You did it! Your checklist is complete. Pick a template and hit 'Preview PDF' and then 'Download PDF' to create your resume!",
    event: null,
    skippable: false,
    hasScrim: true,
    checkComplete: null,
  },
]

export const TOTAL_SETUP_STEPS = SETUP_STEPS.length
