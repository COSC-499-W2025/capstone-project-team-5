import { getPageComponent } from '../app/navigation/pageRegistry'
import { getNavItem } from '../app/navigation/navItems'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppShell({ page, setPage, apiOk, user }) {
  const current = getNavItem(page)
  const CurrentPage = getPageComponent(page)

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-ink">
      <Sidebar current={page} onNav={setPage} apiOk={apiOk} user={user} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title={current?.label ?? page} apiOk={apiOk} />
        <main className="flex-1 overflow-y-auto px-9 py-8">
          <CurrentPage page={page} />
        </main>
      </div>
    </div>
  )
}
