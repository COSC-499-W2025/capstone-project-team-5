import DashboardPage from '../../pages/dashboard/DashboardPage'
import ProjectsPage from '../../pages/projects/ProjectsPage'
import SkillsPage from '../../pages/skills/SkillsPage'
import ExperiencePage from '../../pages/experience/ExperiencePage'
import EducationPage from '../../pages/education/EducationPage'
import ProfilePage from '../../pages/profile/ProfilePage'
import PortfolioPage from '../../pages/portfolio/PortfolioPage'
import ResumesPage from '../../pages/resumes/ResumesPage'
import ConsentsPage from '../../pages/consents/ConsentsPage'
import ComingSoonPage from '../../pages/shared/ComingSoonPage'

const PAGE_COMPONENTS = {
  dashboard: DashboardPage,
  projects: ProjectsPage,
  skills: SkillsPage,
  experience: ExperiencePage,
  education: EducationPage,
  profile: ProfilePage,
  portfolio: PortfolioPage,
  resumes: ResumesPage,
  consents: ConsentsPage,
}

export function getPageComponent(page) {
  return PAGE_COMPONENTS[page] ?? ComingSoonPage
}
