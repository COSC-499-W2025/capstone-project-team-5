/**
 * @jest-environment jsdom
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { AppContext } from '../renderer/src/app/context/AppContext'
import useCrudList from '../renderer/src/hooks/useCrudList'

const EMPTY_FORM = { name: '', age: '' }

const ITEM = { id: 1, name: 'Alice', age: 30 }
const ITEM_UPDATED = { id: 1, name: 'Alice', age: 31 }

function makeApi(overrides = {}) {
  return {
    list: jest.fn().mockResolvedValue([ITEM]),
    create: jest.fn().mockResolvedValue(ITEM),
    update: jest.fn().mockResolvedValue(ITEM_UPDATED),
    remove: jest.fn().mockResolvedValue(null),
    ...overrides,
  }
}

const CTX = { user: { username: 'alice' }, apiOk: true }

function renderCrudHook(opts = {}) {
  const api = opts.api ?? makeApi(opts.apiOverrides)
  return renderHook(
    () =>
      useCrudList({
        emptyForm: EMPTY_FORM,
        api,
        ...opts,
      }),
    {
      wrapper: ({ children }) => (
        <AppContext.Provider value={CTX}>{children}</AppContext.Provider>
      ),
    },
  )
}

beforeEach(() => {
  jest.clearAllMocks()
})

test('loads items on mount', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(api.list).toHaveBeenCalledWith('alice')
  expect(result.current.items).toEqual([ITEM])
  expect(result.current.error).toBe('')
})

test('sets error when list fails', async () => {
  const api = makeApi({ list: jest.fn().mockRejectedValue(new Error('Network error')) })
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.error).toBe('Network error')
  expect(result.current.items).toEqual([])
})

test('openCreate shows form with empty values', async () => {
  const { result } = renderCrudHook()
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  expect(result.current.showForm).toBe(true)
  expect(result.current.editingId).toBeNull()
  expect(result.current.form).toEqual(EMPTY_FORM)
})

test('openEdit populates form from item', async () => {
  const { result } = renderCrudHook()
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openEdit(ITEM))
  expect(result.current.showForm).toBe(true)
  expect(result.current.editingId).toBe(1)
  expect(result.current.form).toEqual({ name: 'Alice', age: '30' })
})

test('cancelForm resets form state', async () => {
  const { result } = renderCrudHook()
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  expect(result.current.showForm).toBe(true)
  act(() => result.current.cancelForm())
  expect(result.current.showForm).toBe(false)
  expect(result.current.editingId).toBeNull()
  expect(result.current.formError).toBe('')
})

test('setField updates a single form field', async () => {
  const { result } = renderCrudHook()
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  act(() => result.current.setField('name', 'Bob'))
  expect(result.current.form.name).toBe('Bob')
  expect(result.current.form.age).toBe('')
})

test('handleSave creates item when not editing', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  act(() => result.current.setField('name', 'Bob'))

  await act(async () => {
    await result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(api.create).toHaveBeenCalledWith('alice', { name: 'Bob', age: '' })
  expect(result.current.showForm).toBe(false)
  expect(result.current.items).toHaveLength(2)
})

test('handleSave updates item when editing', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openEdit(ITEM))
  act(() => result.current.setField('age', '31'))

  await act(async () => {
    await result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(api.update).toHaveBeenCalledWith('alice', 1, { name: 'Alice', age: '31' })
  expect(result.current.items[0]).toEqual(ITEM_UPDATED)
  expect(result.current.showForm).toBe(false)
})

test('handleSave shows formError when validate returns a message', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({
    api,
    validate: (form) => (form.name ? null : 'Name is required.'),
  })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())

  await act(async () => {
    await result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(result.current.formError).toBe('Name is required.')
  expect(api.create).not.toHaveBeenCalled()
  expect(result.current.showForm).toBe(true)
})

test('handleSave uses buildPayload to transform form', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({
    api,
    buildPayload: (form) => ({ ...form, age: parseInt(form.age, 10) || null }),
  })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  act(() => result.current.setField('name', 'Bob'))
  act(() => result.current.setField('age', '25'))

  await act(async () => {
    await result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(api.create).toHaveBeenCalledWith('alice', { name: 'Bob', age: 25 })
})

test('handleSave shows formError on API failure', async () => {
  const api = makeApi({ create: jest.fn().mockRejectedValue(new Error('Server error')) })
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  act(() => result.current.setField('name', 'Bob'))

  await act(async () => {
    await result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(result.current.formError).toBe('Server error')
  expect(result.current.showForm).toBe(true)
})

test('handleDelete removes item and clears confirmId', async () => {
  const api = makeApi()
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.setConfirmId(1))
  expect(result.current.confirmId).toBe(1)

  await act(async () => {
    await result.current.handleDelete(1)
  })

  expect(api.remove).toHaveBeenCalledWith('alice', 1)
  expect(result.current.items).toEqual([])
  expect(result.current.confirmId).toBeNull()
})

test('handleDelete shows error on API failure', async () => {
  const api = makeApi({ remove: jest.fn().mockRejectedValue(new Error('Delete failed')) })
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))

  await act(async () => {
    await result.current.handleDelete(1)
  })

  expect(result.current.error).toBe('Delete failed')
  expect(result.current.items).toEqual([ITEM])
})

test('custom itemToForm overrides default mapping', async () => {
  const { result } = renderCrudHook({
    itemToForm: (item) => ({ name: item.name.toUpperCase(), age: String(item.age) }),
  })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openEdit(ITEM))
  expect(result.current.form).toEqual({ name: 'ALICE', age: '30' })
})

test('defaultItemToForm handles null values with emptyForm defaults', async () => {
  const api = makeApi({ list: jest.fn().mockResolvedValue([{ id: 2, name: null, age: null }]) })
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openEdit({ id: 2, name: null, age: null }))
  expect(result.current.form).toEqual({ name: '', age: '' })
})

test('saving is true during save and false after', async () => {
  let resolveCreate
  const api = makeApi({
    create: jest.fn().mockImplementation(() => new Promise((r) => { resolveCreate = r })),
  })
  const { result } = renderCrudHook({ api })
  await waitFor(() => expect(result.current.loading).toBe(false))
  act(() => result.current.openCreate())
  act(() => result.current.setField('name', 'Bob'))

  let savePromise
  act(() => {
    savePromise = result.current.handleSave({ preventDefault: jest.fn() })
  })

  expect(result.current.saving).toBe(true)

  await act(async () => {
    resolveCreate(ITEM)
    await savePromise
  })

  expect(result.current.saving).toBe(false)
})
