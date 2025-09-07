import { NextPageContext } from 'next'

interface ErrorProps {
  statusCode?: number
}

function Error({ statusCode }: ErrorProps) {
  return (
    <div className="min-h-screen bg-[var(--ow-bg)] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-[var(--ow-ink)] mb-4">
          {statusCode ? `${statusCode} - ` : ''}Something went wrong
        </h1>
        <p className="text-[var(--ow-ink-dim)] mb-6">
          {statusCode
            ? `An error ${statusCode} occurred on server`
            : 'An error occurred on client'}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-[var(--ow-primary)] text-white px-4 py-2 rounded hover:bg-[var(--ow-primary-hover)]"
        >
          Reload Page
        </button>
      </div>
    </div>
  )
}

Error.getInitialProps = ({ res, err }: NextPageContext) => {
  const statusCode = res ? res.statusCode : err ? err.statusCode : 404
  return { statusCode }
}

export default Error 