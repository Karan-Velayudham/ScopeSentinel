import { render, screen } from '@testing-library/react'
import { HitlBanner } from './hitl-banner'
import '@testing-library/jest-dom'

describe('HitlBanner', () => {
    it('renders the waiting for approval message', () => {
        // In our implementation, hasPendingApproval is hardcoded to true
        // and pendingRunId is "run-126"
        render(<HitlBanner />)
        expect(screen.getByText(/Waiting for your approval on Run run-126/i)).toBeInTheDocument()
        expect(screen.getByRole('link', { name: /Review Now/i })).toHaveAttribute('href', '/runs/run-126')
    })
})
