import DashboardPage from '../../pages/dashboard/DashboardPage'
import ProjectsPage from '../../pages/projects/ProjectsPage'
import SkillsPage from '../../pages/skills/SkillsPage'
import ExperiencePage from '../../pages/experience/ExperiencePage'
import EducationPage from '../../pages/education/EducationPage'
import PortfolioPage from '../../pages/portfolio/PortfolioPage'
import ResumesPage from '../../pages/resumes/ResumesPage'
import ComingSoonPage from '../../pages/shared/ComingSoonPage'

const PAGE_COMPONENTS = {
  dashboard: DashboardPage,
  projects: ProjectsPage,
  skills: SkillsPage,
  experience: ExperiencePage,
  education: EducationPage,
  portfolio: PortfolioPage,
  resumes: ResumesPage,
}

export function getPageComponent(page) {
  return PAGE_COMPONENTS[page] ?? ComingSoonPage
}
