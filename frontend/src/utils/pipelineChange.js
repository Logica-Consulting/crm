/**
 * Helper functions for pipeline change confirmation and validation
 */

/**
 * Check if a pipeline change is happening and requires confirmation
 * @param {Object} currentDeal - Current deal object
 * @param {Object} newValues - New values being set
 * @returns {boolean} - Whether pipeline change confirmation is needed
 */
export function requiresPipelineChangeConfirmation(currentDeal, newValues) {
  const currentPipeline = currentDeal?.comercial_pipeline
  const newPipeline = newValues?.comercial_pipeline

  // Check if pipeline is changing and both values exist
  if (currentPipeline && newPipeline && currentPipeline !== newPipeline) {
    return true
  }

  return false
}

/**
 * Generate confirmation message for pipeline change
 * @param {string} oldPipeline - Previous pipeline
 * @param {string} newPipeline - New pipeline
 * @returns {string} - Confirmation message
 */
export function getPipelineChangeMessage(oldPipeline, newPipeline) {
  return `Pipeline is changing from "${oldPipeline}" to "${newPipeline}". This will reset the deal status to the first stage of the new pipeline. Are you sure you want to proceed?`
}

/**
 * Validate that a status belongs to the selected pipeline
 * @param {string} status - Status name
 * @param {string} pipeline - Pipeline name
 * @returns {Promise<boolean>} - Whether status is valid for pipeline
 */
export async function validateStatusForPipeline(status, pipeline) {
  if (!status || !pipeline) {
    return false
  }

  try {
    // Get all stages for the pipeline
    const response = await frappe.call({
      method: 'comercial.api.pipeline.get_pipeline_stages',
      args: {
        pipeline_type: pipeline,
      },
    })

    if (response?.message) {
      const stages = response.message
      return stages.some((stage) => stage.stage_name === status)
    }

    return false
  } catch (error) {
    console.error('Error validating status for pipeline:', error)
    return false
  }
}

/**
 * Show pipeline change confirmation dialog using frappe.ui.Dialog
 * @param {string} oldPipeline - Previous pipeline
 * @param {string} newPipeline - New pipeline
 * @returns {Promise<boolean>} - Whether user confirmed the change
 */
export async function showPipelineChangeConfirmation(
  oldPipeline,
  newPipeline,
  renderDialog,
) {
  if (typeof renderDialog !== 'function') return false

  const escapeHtml = (value) =>
    String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }
      return entities[character]
    })

  const message = getPipelineChangeMessage(oldPipeline, newPipeline)
  const result = await renderDialog({
    title: __('Confirm Pipeline Change'),
    fields: [
      {
        fieldtype: 'HTML',
        options: `<p>${escapeHtml(message)}</p>`,
      },
    ],
    actions: [
      {
        label: __('Confirm'),
        variant: 'solid',
        onClick: ({ close }) => close(true),
      },
      {
        label: __('Cancel'),
        onClick: ({ close }) => close(false),
      },
    ],
  })

  // The native form dialog resolves null for Escape, overlay, or close.
  return result === true
}

export function createRollbackOnError(resolveDoc, previousValues, onError) {
  return (error) => {
    const doc = typeof resolveDoc === 'function' ? resolveDoc() : resolveDoc
    Object.assign(doc, previousValues)
    onError?.(error)
  }
}
