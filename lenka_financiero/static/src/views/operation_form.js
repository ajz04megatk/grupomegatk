/** @odoo-module **/

import { onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class LenkaOperationFormController extends FormController {
    setup() {
        super.setup();
        this.guidanceFrame = null;
        this.clearGuidance = () => {};
        onWillUnmount(() => {
            cancelAnimationFrame(this.guidanceFrame);
            this.clearGuidance();
        });
    }

    async beforeExecuteActionButton(params) {
        const record = this.model.root;
        if (params.name === "action_mark_contracted" &&
            record.data.state === "approved" && !record.data.contract_signed) {
            const guide = () => this.showContractGuidance();
            this.dialogService.add(AlertDialog, {
                title: "Falta confirmar la firma",
                body: "En Aprobación y contrato, marcá Contrato firmado únicamente cuando el contrato ya esté firmado. También debe existir el contrato firmado y adjunto en Contratos y documentos.",
                confirmLabel: "Cerrar e ir al campo",
                confirm: guide,
                dismiss: guide,
            });
            // Keep all draft edits and do not execute the server action yet.
            return false;
        }
        return super.beforeExecuteActionButton(params);
    }

    showContractGuidance() {
        this.clearGuidance();
        const root = this.rootRef.el;
        if (!root) {
            return;
        }
        root.querySelector('[role="tab"][name="approval_contract"]')?.click();
        // Allow the notebook and closing dialog to render before moving focus.
        cancelAnimationFrame(this.guidanceFrame);
        this.guidanceFrame = requestAnimationFrame(() => {
            this.guidanceFrame = requestAnimationFrame(() => {
                const field = root.querySelector('.o_field_widget[name="contract_signed"]');
                const input = field?.querySelector('input[type="checkbox"]');
                if (!field || !input) {
                    return;
                }
                field.classList.add("o_lenka_needs_attention");
                input.setAttribute("aria-invalid", "true");
                const hint = document.createElement("span");
                hint.className = "o_lenka_validation_hint";
                hint.textContent = "Pendiente: confirmar que el contrato está firmado.";
                hint.setAttribute("role", "alert");
                field.appendChild(hint);
                this.clearGuidance = () => {
                    field.classList.remove("o_lenka_needs_attention");
                    input.removeAttribute("aria-invalid");
                    hint.remove();
                    input.removeEventListener("change", clearWhenCorrected);
                };
                const clearWhenCorrected = () => {
                    if (input.checked) {
                        this.clearGuidance();
                    }
                };
                input.addEventListener("change", clearWhenCorrected);
                field.scrollIntoView({ block: "center", behavior: "smooth" });
                input.focus({ preventScroll: true });
            });
        });
    }
}

registry.category("views").add("lenka_operation_form", {
    ...formView,
    Controller: LenkaOperationFormController,
});
