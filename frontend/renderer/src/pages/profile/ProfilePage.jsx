import InlineError from '../../components/InlineError'
import PageHeader from '../../components/PageHeader'
import useSingletonForm from '../../hooks/useSingletonForm'

const EMPTY_FORM = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  linkedin_url: '',
  github_username: '',
  website: '',
}

const API = {
  get: (username) => window.api.getProfile(username),
  create: (username, data) => window.api.createProfile(username, data),
  update: (username, data) => window.api.updateProfile(username, data),
}

function validate(form) {
  if (!form.first_name.trim() || !form.last_name.trim()) {
    return 'First name and last name are required.'
  }
  return null
}

function buildPayload(form) {
  return {
    first_name: form.first_name.trim() || null,
    last_name: form.last_name.trim() || null,
    email: form.email.trim() || null,
    phone: form.phone.trim() || null,
    address: form.address.trim() || null,
    city: form.city.trim() || null,
    state: form.state.trim() || null,
    zip_code: form.zip_code.trim() || null,
    linkedin_url: form.linkedin_url.trim() || null,
    github_username: form.github_username.trim() || null,
    website: form.website.trim() || null,
  }
}

function DetailRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-muted">{label}:</span>
      <span className="text-ink">{value}</span>
    </div>
  )
}
export default function ProfilePage() {
  const {
    data, form, error, formError, loading, saving, exists, showForm,
    openCreate, openEdit, cancelForm, setField, handleSave,
  } = useSingletonForm({ emptyForm: EMPTY_FORM, api: API, validate, buildPayload })
  return (
    <div className="animate-fade-up space-y-6">
      <PageHeader
        title="Profile"
        description="Manage your personal and contact information for resumes."
        action={!showForm && exists && (
          <button type="button" className="btn-primary text-xs" onClick={openEdit}>
            Edit
          </button>
        )}
      />
      <InlineError message={error} />
      {showForm && (
        <form onSubmit={handleSave} className="card space-y-4 p-5">
          <h2 className="text-sm font-bold">
            {exists ? 'Edit Profile' : 'New Profile'}
          </h2>
          <InlineError message={formError} />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              className="input"
              placeholder="First Name *"
              required
              value={form.first_name}
              onChange={(e) => setField('first_name', e.target.value)}
            />
            <input
              className="input"
              placeholder="Last Name *"
              required
              value={form.last_name}
              onChange={(e) => setField('last_name', e.target.value)}
            />
            <input
              className="input"
              placeholder="Email"
              type="email"
              value={form.email}
              onChange={(e) => setField('email', e.target.value)}
            />
            <input
              className="input"
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setField('phone', e.target.value)}
            />
            <input
              className="input"
              placeholder="Address"
              value={form.address}
              onChange={(e) => setField('address', e.target.value)}
            />
            <input
              className="input"
              placeholder="City"
              value={form.city}
              onChange={(e) => setField('city', e.target.value)}
            />
            <input
              className="input"
              placeholder="State"
              value={form.state}
              onChange={(e) => setField('state', e.target.value)}
            />
            <input
              className="input"
              placeholder="ZIP Code"
              value={form.zip_code}
              onChange={(e) => setField('zip_code', e.target.value)}
            />
            <input
              className="input"
              placeholder="LinkedIn URL"
              type="url"
              value={form.linkedin_url}
              onChange={(e) => setField('linkedin_url', e.target.value)}
            />
            <input
              className="input"
              placeholder="GitHub Username"
              value={form.github_username}
              onChange={(e) => setField('github_username', e.target.value)}
            />
            <input
              className="input md:col-span-2"
              placeholder="Website"
              type="url"
              value={form.website}
              onChange={(e) => setField('website', e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-xs" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="btn-ghost text-xs" onClick={cancelForm}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {loading && (
        <div className="flex justify-center py-12">
          <span className="spinner" />
        </div>
      )}
      {!loading && !showForm && exists && data && (
        <div className="card space-y-3 p-5">
          <h3 className="text-sm font-bold">
            {data.first_name} {data.last_name}
          </h3>
          <div className="grid grid-cols-1 gap-1 md:grid-cols-2">
            <DetailRow label="Email" value={data.email} />
            <DetailRow label="Phone" value={data.phone} />
            <DetailRow label="Address" value={data.address} />
            <DetailRow label="City" value={data.city} />
            <DetailRow label="State" value={data.state} />
            <DetailRow label="ZIP Code" value={data.zip_code} />
            <DetailRow label="LinkedIn" value={data.linkedin_url} />
            <DetailRow label="GitHub" value={data.github_username} />
            <DetailRow label="Website" value={data.website} />
          </div>
        </div>
      )}
      {!loading && !showForm && !exists && (
        <div className="space-y-3">
          <p className="text-xs text-muted">No profile yet. Add one to get started.</p>
          <button type="button" className="btn-primary text-xs" onClick={openCreate}>
            + Add Profile
          </button>
        </div>
      )}
    </div>
  )
}
