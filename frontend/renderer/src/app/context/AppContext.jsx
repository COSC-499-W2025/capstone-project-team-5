import { createContext, useContext } from 'react'

/**
 * Shape:
 *   user, apiOk, page, setPage,
 *   uploadHighlights, setUploadHighlights,
 *   logout   ← clears credentials and returns to the consent/login gate
 */
export const AppContext = createContext(null)

export function useApp() {
  return useContext(AppContext)
}
