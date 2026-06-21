import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { exec } from "child_process";
import { promisify } from "util";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

const execAsync = promisify(exec);

export default function (pi: ExtensionAPI) {
  // Helper to find the absolute path of run.sh in the project workspace
  const getLauncherPath = (): string => {
    // Attempt to use current directory or locate run.sh in parent directories
    let dir = process.cwd();
    while (dir && dir !== path.parse(dir).root) {
      const launcher = path.join(dir, "run.sh");
      if (fs.existsSync(launcher)) {
        return launcher;
      }
      dir = path.dirname(dir);
    }
    return "./run.sh"; // Fallback to relative
  };

  const runCommand = async (args: string[]): Promise<string> => {
    const launcher = getLauncherPath();
    const cmd = `"${launcher}" ${args.map(a => `"${a.replace(/"/g, '\\"')}"`).join(" ")}`;
    
    try {
      const { stdout, stderr } = await execAsync(cmd, { cwd: path.dirname(launcher) });
      return stdout + "\n" + stderr;
    } catch (error: any) {
      throw new Error(`Execution failed: ${error.message}\nOutput: ${error.stdout || ""}\nError: ${error.stderr || ""}`);
    }
  };

  // 1. Tool: concur_list_reports
  pi.registerTool({
    name: "concur_list_reports",
    label: "List Concur Reports",
    description: "Queries and lists active or historical expense reports in SAP Concur.",
    parameters: Type.Object({
      filter_view: Type.Optional(Type.String({
        description: "Dropdown filter to apply (e.g., 'Last 90 Days', 'All Reports', 'Active Reports')",
        default: "Last 90 Days"
      })),
      is_old: Type.Optional(Type.Boolean({
        description: "Set true to query historical reports, false for current active/draft reports",
        default: true
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const filter = params.filter_view || "Last 90 Days";
      const isOld = params.is_old !== false;
      
      const args = isOld ? ["browser-query-old", filter] : ["browser-query"];
      const output = await runCommand(args);
      
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 2. Tool: concur_report_details
  pi.registerTool({
    name: "concur_report_details",
    label: "Get Concur Report Details",
    description: "Fetches full metadata and line-item details of a specific expense report by name.",
    parameters: Type.Object({
      report_name: Type.String({ description: "The exact name of the target expense report" }),
      filter_view: Type.Optional(Type.String({
        description: "The view filter to look inside (e.g., 'Last 90 Days', 'All Reports')",
        default: "Last 90 Days"
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const filter = params.filter_view || "Last 90 Days";
      const output = await runCommand(["browser-report-details", params.report_name, filter]);
      
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 3. Tool: concur_list_cards
  pi.registerTool({
    name: "concur_list_card_transactions",
    label: "List Card Transactions",
    description: "Queries and lists credit card transactions inside the Available Expenses section.",
    parameters: Type.Object({
      filter_view: Type.Optional(Type.String({
        description: "The activity filter to apply (e.g., 'All Corporate and Personal Cards', 'All Purchasing Cards')",
        default: "All Corporate and Personal Cards"
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const filter = params.filter_view || "All Corporate and Personal Cards";
      const output = await runCommand(["browser-list-cards", filter]);
      
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 4. Tool: concur_reconcile_report
  pi.registerTool({
    name: "concur_reconcile_report",
    label: "Reconcile Concur Report",
    description: "Automates month-end reconciliation: fills in Expense Type, Purpose, Comment, and Allocation Codes for each transaction in the report, and optionally submits the report.",
    parameters: Type.Object({
      report_name: Type.String({ description: "Name of the draft expense report to reconcile" }),
      rules: Type.String({
        description: "JSON string representing mapping rules. Keys are merchant names (e.g., 'Uber'), values map to expense_type, business_purpose, comment, allocation_code."
      }),
      submit: Type.Optional(Type.Boolean({
        description: "Whether to submit the report after reconciling (default: false, leaving report in draft mode for review)",
        default: false
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      // Validate JSON rules
      let rulesObj;
      try {
        rulesObj = JSON.parse(params.rules);
      } catch (err: any) {
        throw new Error(`Invalid JSON rules input: ${err.message}`);
      }

      // Write rules temporarily to file
      const tempFile = path.join(os.tmpdir(), `concur-recon-${Date.now()}.json`);
      fs.writeFileSync(tempFile, JSON.stringify(rulesObj, null, 2));

      try {
        const cmdArgs = ["browser-reconcile", params.report_name, tempFile];
        if (params.submit) {
          cmdArgs.push("--submit");
        }
        const output = await runCommand(cmdArgs);
        return {
          content: [{ type: "text", text: output }],
          details: {}
        };
      } finally {
        if (fs.existsSync(tempFile)) {
          fs.unlinkSync(tempFile);
        }
      }
    }
  });

  // 5. Tool: concur_attach_receipt
  pi.registerTool({
    name: "concur_attach_receipt",
    label: "Attach Receipt to Expense",
    description: "Attaches a local receipt image or PDF file directly to a transaction inside an expense report.",
    parameters: Type.Object({
      report_name: Type.String({ description: "Name of the expense report containing the transaction" }),
      merchant: Type.String({ description: "Merchant name or transaction ID to match receipt against (e.g., 'Uber')" }),
      receipt_path: Type.String({ description: "Absolute local path to the receipt file (PDF or image)" })
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const output = await runCommand([
        "browser-attach-receipt",
        params.report_name,
        params.merchant,
        params.receipt_path
      ]);
      
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 6. Tool: concur_create_report
  pi.registerTool({
    name: "concur_create_report",
    label: "Create Draft Report",
    description: "Creates a new draft expense report headlessly.",
    parameters: Type.Object({
      name: Type.String({ description: "Name of the expense report to create" }),
      purpose: Type.Optional(Type.String({ description: "Business purpose of the report" })),
      comment: Type.Optional(Type.String({ description: "Optional comment or description for the report" }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const args = ["browser-create"];
      if (params.name) args.push(params.name);
      if (params.purpose) args.push(params.purpose);
      if (params.comment) args.push(params.comment);
      
      const output = await runCommand(args);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 7. Tool: concur_delete_report
  pi.registerTool({
    name: "concur_delete_report",
    label: "Delete Draft Report",
    description: "Deletes a draft expense report by name.",
    parameters: Type.Object({
      report_name: Type.String({ description: "The exact name of the draft report to delete" })
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const output = await runCommand(["browser-delete", params.report_name]);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 8. Tool: concur_card_transaction_details
  pi.registerTool({
    name: "concur_card_transaction_details",
    label: "Get Card Transaction Details",
    description: "Fetches details of a specific credit card transaction by merchant or ID.",
    parameters: Type.Object({
      merchant_or_id: Type.String({ description: "Merchant name or transaction ID to look up (e.g., 'Uber', 'TX_5002')" }),
      filter_view: Type.Optional(Type.String({
        description: "Dropdown filter to look inside (e.g., 'All Corporate and Personal Cards', 'All Purchasing Cards')",
        default: "All Corporate and Personal Cards"
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const filter = params.filter_view || "All Corporate and Personal Cards";
      const output = await runCommand(["browser-card-details", params.merchant_or_id, filter]);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 9. Tool: concur_add_delegate
  pi.registerTool({
    name: "concur_add_delegate",
    label: "Add Expense Delegate",
    description: "Adds a new expense delegate in settings with specified permissions.",
    parameters: Type.Object({
      name_or_email: Type.String({ description: "Full name or email address of the delegate to add" }),
      permissions: Type.Optional(Type.Array(Type.String(), {
        description: "List of permissions to assign (e.g. ['prepare', 'submit', 'approve'])",
        default: ["prepare"]
      }))
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const perms = params.permissions || ["prepare"];
      const output = await runCommand(["browser-add-delegate", params.name_or_email, ...perms]);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 10. Tool: concur_remove_delegate
  pi.registerTool({
    name: "concur_remove_delegate",
    label: "Remove Expense Delegate",
    description: "Removes an expense delegate from settings by name or email.",
    parameters: Type.Object({
      name_or_email: Type.String({ description: "Full name or email address of the delegate to remove" })
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const output = await runCommand(["browser-remove-delegate", params.name_or_email]);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });

  // 11. Tool: concur_nuke_drafts_and_receipts
  pi.registerTool({
    name: "concur_nuke_drafts_and_receipts",
    label: "Nuke Drafts and Receipts",
    description: "Deletes all draft reports and available receipts inside Concur (intended for testing cleanup).",
    parameters: Type.Object({}),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const output = await runCommand(["browser-nuke"]);
      return {
        content: [{ type: "text", text: output }],
        details: {}
      };
    }
  });
}
