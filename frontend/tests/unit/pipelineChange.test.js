import { describe, it, expect } from 'vitest'
import {
  requiresPipelineChangeConfirmation,
  getPipelineChangeMessage,
  showPipelineChangeConfirmation,
  createRollbackOnError,
} from '../../src/utils/pipelineChange'

describe('pipelineChange utilities', () => {
  describe('requiresPipelineChangeConfirmation', () => {
    it('should return true when pipeline is changing', () => {
      const currentDeal = { comercial_pipeline: 'Transactional' }
      const newValues = { comercial_pipeline: 'SIPRA' }

      const result = requiresPipelineChangeConfirmation(currentDeal, newValues)

      expect(result).toBe(true)
    })

    it('should return false when pipeline is not changing', () => {
      const currentDeal = { comercial_pipeline: 'Transactional' }
      const newValues = { comercial_pipeline: 'Transactional' }

      const result = requiresPipelineChangeConfirmation(currentDeal, newValues)

      expect(result).toBe(false)
    })

    it('should return false when current pipeline is undefined', () => {
      const currentDeal = { comercial_pipeline: undefined }
      const newValues = { comercial_pipeline: 'SIPRA' }

      const result = requiresPipelineChangeConfirmation(currentDeal, newValues)

      expect(result).toBe(false)
    })

    it('should return false when new pipeline is undefined', () => {
      const currentDeal = { comercial_pipeline: 'Transactional' }
      const newValues = { comercial_pipeline: undefined }

      const result = requiresPipelineChangeConfirmation(currentDeal, newValues)

      expect(result).toBe(false)
    })
  })

  describe('getPipelineChangeMessage', () => {
    it('should return correct confirmation message', () => {
      const message = getPipelineChangeMessage('Transactional', 'SIPRA')

      expect(message).toBe(
        'Pipeline is changing from "Transactional" to "SIPRA". This will reset the deal status to the first stage of the new pipeline. Are you sure you want to proceed?',
      )
    })
  })

  describe('showPipelineChangeConfirmation', () => {
    it('uses the injected native dialog renderer and resolves acceptance', async () => {
      let options
      const confirmed = await showPipelineChangeConfirmation(
        'Transactional',
        'SIPRA',
        async (dialogOptions) => {
          options = dialogOptions
          return true
        },
      )

      expect(confirmed).toBe(true)
      expect(options.title).toBe('Confirm Pipeline Change')
      expect(options.actions).toHaveLength(2)
      expect(options.fields[0].fieldtype).toBe('HTML')
      let actionResult
      options.actions[0].onClick({ close: (value) => (actionResult = value) })
      expect(actionResult).toBe(true)
    })

    it('treats a native dialog close or cancel as rejection', async () => {
      await expect(
        showPipelineChangeConfirmation(
          'Transactional',
          'SIPRA',
          async () => null,
        ),
      ).resolves.toBe(false)
    })

    it('does not proceed when the dialog renderer is unavailable', async () => {
      await expect(
        showPipelineChangeConfirmation('Transactional', 'SIPRA'),
      ).resolves.toBe(false)
    })
  })

  describe('createRollbackOnError', () => {
    it('restores the live resource document after a failed save replaces its object', () => {
      const resource = {
        doc: { status: 'SIPRA Commercial Closure' },
      }
      const originalDoc = resource.doc
      const rollback = createRollbackOnError(() => resource.doc, {
        status: 'SIPRA Group Demo',
      })

      // documentResource's error handler can replace doc before calling onError.
      resource.doc = { status: 'SIPRA Commercial Closure' }
      const rejectedDoc = resource.doc
      rollback({ status: 417 })

      expect(resource.doc).toBe(rejectedDoc)
      expect(resource.doc.status).toBe('SIPRA Group Demo')
      expect(originalDoc.status).toBe('SIPRA Commercial Closure')
    })

    it('restores all captured values before reporting a rejected save', () => {
      const doc = { status: 'SIPRA Group Demo', comercial_pipeline: 'SIPRA' }
      const errors = []
      const rollback = createRollbackOnError(
        doc,
        { status: 'SIPRA Group Demo', comercial_pipeline: 'SIPRA' },
        (error) => errors.push(error),
      )

      doc.status = 'SIPRA Commercial Closure'
      doc.comercial_pipeline = 'Consultative'
      const rejection = { status: 417, messages: ['stage transition rejected'] }
      rollback(rejection)

      expect(doc).toEqual({
        status: 'SIPRA Group Demo',
        comercial_pipeline: 'SIPRA',
      })
      expect(errors).toEqual([rejection])
    })
  })
})
