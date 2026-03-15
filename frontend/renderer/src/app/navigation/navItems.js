export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '◈' },
  { id: 'projects', label: 'Projects', icon: '◻' },
  { id: 'skills', label: 'Skills', icon: '◆' },
  { id: 'experience', label: 'Experience', icon: '◎' },
  { id: 'education', label: 'Education', icon: '▣' },
  { id: 'profile', label: 'Profile', icon: '◉' },
  { id: 'portfolio', label: 'Portfolio', icon: '⬡' },
  { id: 'resumes', label: 'Resumes', icon: '▤' },
  { id: 'consents', label: 'Consents', icon: '◬' },
]

export function getNavItem(page) {
  return NAV_ITEMS.find((item) => item.id === page) ?? null
}
