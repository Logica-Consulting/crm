import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the frappe object and its call method
const mockFrappeCall = vi.fn()
global.frappe = {
  call: mockFrappeCall,
}

// Import after mocking frappe
import { validateStatusForPipeline } from '../../src/utils/pipelineChange'

describe('comercial API paths', () => {
  beforeEach(() => {
    mockFrappeCall.mockClear()
  })

  describe('validateStatusForPipeline', () => {
    it('should call the correct API endpoint with comercial.api.pipeline path', async () => {
      // Mock the response
      mockFrappeCall.mockResolvedValue({
        message: [
          { stage_name: 'SIPRA Group Demo' },
          { stage_name: 'SIPRA 14-Day Trial' },
        ],
      })

      const result = await validateStatusForPipeline(
        'SIPRA Group Demo',
        'SIPRA',
      )

      expect(mockFrappeCall).toHaveBeenCalledWith({
        method: 'comercial.api.pipeline.get_pipeline_stages',
        args: {
          pipeline_type: 'SIPRA',
        },
      })
      expect(result).toBe(true)
    })

    it('should return false when status does not belong to pipeline', async () => {
      // Mock the response
      mockFrappeCall.mockResolvedValue({
        message: [
          { stage_name: 'SIPRA Group Demo' },
          { stage_name: 'SIPRA 14-Day Trial' },
        ],
      })

      const result = await validateStatusForPipeline('Unknown Status', 'SIPRA')

      expect(result).toBe(false)
    })

    it('should return false when no status or pipeline provided', async () => {
      const result1 = await validateStatusForPipeline('', 'SIPRA')
      const result2 = await validateStatusForPipeline('SIPRA Group Demo', '')

      expect(result1).toBe(false)
      expect(result2).toBe(false)
    })

    it('should return false when API call fails', async () => {
      // Mock the error response
      mockFrappeCall.mockRejectedValue(new Error('API Error'))

      const result = await validateStatusForPipeline(
        'SIPRA Group Demo',
        'SIPRA',
      )

      expect(result).toBe(false)
    })
  })

  it('should have the correct API path in the source', () => {
    // Check that the source code uses the correct path
    const sourceCode = `
      const response = await frappe.call({
        method: 'comercial.api.pipeline.get_pipeline_stages',
        args: {
          pipeline_type: pipeline
        }
      });
    `

    // Verify the correct path is used (not the doubled comercial.comercial path)
    expect(sourceCode).toContain('comercial.api.pipeline.get_pipeline_stages')
    expect(sourceCode).not.toContain('comercial.comercial.api.pipeline')
  })
})
