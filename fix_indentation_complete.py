#!/usr/bin/env python3
"""
Comprehensive fix for indentation errors in invoices_page.py
"""

def fix_indentation_complete():
    """Fix all indentation errors in the invoices_page.py file."""
    
    # Read the file
    with open('app/invoices_page.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the incomplete detect_status_changes function
    old_function = '''def detect_status_changes(previous_invoices, current_invoices):
    """Detect status changes between previous and current invoice lists."""
    changes = []
    if not previous_invoices:
        return changes
    prev_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in previous_invoices}
    curr_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in current_invoices}
    for inv_id, current_status in curr_lookup.items():
        if inv_id in prev_lookup:
            previous_status = prev_lookup[inv_id]
            if previous_status != current_status:'''
    
    new_function = '''def detect_status_changes(previous_invoices, current_invoices):
    """Detect status changes between previous and current invoice lists."""
    changes = []
    if not previous_invoices:
        return changes
    prev_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in previous_invoices}
    curr_lookup = {inv.get('id'): inv.get('status', 'pending') for inv in current_invoices}
    for inv_id, current_status in curr_lookup.items():
        if inv_id in prev_lookup:
            previous_status = prev_lookup[inv_id]
            if previous_status != current_status:
                invoice_number = next((inv.get('invoice_number', 'Unknown') for inv in current_invoices if inv.get('id') == inv_id), 'Unknown')
                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")
    return changes'''
    
    # Replace the incomplete function
    content = content.replace(old_function, new_function)
    
    # Remove orphaned lines that are not part of any function
    lines_to_remove = [
        '                invoice_number = next((inv.get(\'invoice_number\', \'Unknown\') for inv in current_invoices if inv.get(\'id\') == inv_id), \'Unknown\')\n',
        '                changes.append(f"Invoice {invoice_number} changed from {previous_status} to {current_status}")\n',
        '    return changes\n',
        '                    status_changes = detect_status_changes(st.session_state.get(\'previous_invoices\', []), invoices)\n',
        '                    if status_changes:\n',
        '                        for change in status_changes:\n',
        '                            announce_to_screen_reader(f"Status update: {change}", \'polite\')\n',
        '                \n',
        '                # Store current state for next comparison\n',
        '                st.session_state.previous_invoices = invoices.copy()\n',
        '                \n',
        '            except Exception as e:\n',
        '                st.warning(f"⚠️ Unable to refresh statuses: {str(e)}")\n',
        '    \n',
        '    \n',
        '    \n',
        '        \n',
        '        # Handle selection state with enhanced logic\n',
        '        if selected_index is None:\n',
        '            # Use session state if no external selection provided\n',
        '            if \'selected_invoice_idx\' not in st.session_state:\n',
        '                st.session_state.selected_invoice_idx = 0\n',
        '            selected_index = st.session_state.selected_invoice_idx\n',
        '        \n',
        '        # Ensure selected index is valid\n',
        '        if selected_index >= len(invoices):\n',
        '            selected_index = 0 if invoices else None\n',
        '        \n',
        '        if invoices:\n',
        '            # Enhanced header with real-time status summary\n',
        '            status_counts = get_status_counts(invoices)\n',
        '            total_value = sum(inv.get(\'total\', 0) for inv in invoices)\n',
        '            \n',
        '            st.markdown(f\'\'\'\n',
        '                <div style="padding: 0.8rem 0; margin-bottom: 1.2rem; font-size: 0.9rem; color: #666; border-bottom: 1px solid #eee; background: #f8f9fa; border-radius: 8px; padding: 0.8rem;">\n',
        '                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">\n',
        '                        <span style="font-weight: 600; color: #222;">📄 {len(invoices)} invoice{\'s\' if len(invoices) != 1 else \'\'}</span>\n',
        '                        <span style="font-weight: 600; color: #222;">💰 {format_currency(total_value)}</span>\n',
        '                    </div>\n',
        '                    <div style="display: flex; gap: 1rem; font-size: 0.8rem; flex-wrap: wrap;">\n',
        '                        {f\'<span style="color: #4CAF50;">✅ {status_counts["matched"]} matched</span>\' if status_counts["matched"] > 0 else \'\'}\n',
        '                        {f\'<span style="color: #f1c232;">⚠️ {status_counts["discrepancy"]} discrepancies</span>\' if status_counts["discrepancy"] > 0 else \'\'}\n',
        '                        {f\'<span style="color: #ff3b30;">❌ {status_counts["not_paired"]} not paired</span>\' if status_counts["not_paired"] > 0 else \'\'}\n',
        '                        {f\'<span style="color: #007bff;">🔄 {status_counts["processing"]} processing</span>\' if status_counts["processing"] > 0 else \'\'}\n',
        '                        {f\'<span style="color: #888;">⏳ {status_counts["pending"]} pending</span>\' if status_counts["pending"] > 0 else \'\'}\n',
        '                    </div>\n',
        '                    <div style="font-size: 0.75rem; color: #999; margin-top: 0.3rem;">\n',
        '                        🔄 Auto-refreshing every 30 seconds • Last updated: {datetime.now().strftime(\'%H:%M:%S\')}\n',
        '                    </div>\n',
        '                </div>\n',
        '            \'\'\', unsafe_allow_html=True)\n',
        '            \n',
        '            # Enhanced invoice cards with real-time statuses\n',
        '            for idx, inv in enumerate(invoices):\n',
        '                # Get enhanced status information\n',
        '                status = inv.get(\'status\', \'pending\')\n',
        '                status_icon = get_enhanced_status_icon(status)\n',
        '                is_selected = (idx == selected_index)\n',
        '                card_class = "owlin-invoice-card selected" if is_selected else "owlin-invoice-card"\n',
        '                # Add processing animation for processing status\n',
        '                if status == \'processing\':\n',
        '                    card_class += " owlin-processing"\n',
        '                # Create unique key for each invoice card\n',
        '                card_key = f"invoice_card_{inv.get(\'id\', idx)}_{idx}"\n',
        '                # Enhanced invoice data extraction\n',
        '                invoice_number = sanitize_text(inv.get(\'invoice_number\', \'N/A\'))\n',
        '                supplier = sanitize_text(inv.get(\'supplier\', \'N/A\'))\n',
        '                date = sanitize_text(inv.get(\'date\', \'\'))\n',
        '                total = format_currency(inv.get(\'total\', 0))\n',
        '                # Create comprehensive ARIA label for accessibility\n',
        '                aria_label = f"Invoice {invoice_number} from {supplier}, {status} status, total {total}, {date}"\n',
        '                if is_selected:\n',
        '                    aria_label += ", currently selected"\n',
        '                # Enhanced clickable invoice card with keyboard support\n',
        '                if st.button(\n',
        '                    f"Select {invoice_number} from {supplier}", \n',
        '                    key=card_key, \n',
        '                    help=f"Select invoice {invoice_number} from {supplier} (Status: {status})",\n',
        '                    use_container_width=True\n',
        '                ):\n',
        '                    # Handle selection with enhanced feedback\n',
        '                    if on_select:\n',
        '                        # Use external callback if provided\n',
        '                        on_select(idx, inv)\n',
        '                    else:\n',
        '                        # Update session state\n',
        '                        st.session_state.selected_invoice_idx = idx\n',
        '                        announce_to_screen_reader(f"Selected invoice {invoice_number} from {supplier}")\n',
        '                        st.rerun()\n',
        '                # Enhanced invoice card rendering with real-time status\n',
        '                st.markdown(f\'\'\'\n',
        '                    <div class="{card_class}" \n',
        '                         role="listitem" \n',
        '                         aria-label="{aria_label}"\n',
        '                         aria-selected="{str(is_selected).lower()}"\n',
        '                         data-invoice-id="{inv.get(\'id\', \'\')}"\n',
        '                         data-invoice-number="{invoice_number}"\n',
        '                         data-supplier="{supplier}"\n',
        '                         data-status="{status}"\n',
        '                         tabindex="0"\n',
        '                         onkeydown="handleInvoiceCardKeydown(event, {idx})"\n',
        '                         onclick="selectInvoiceCard({idx})"\n',
        '                         style="cursor: pointer; transition: all 0.2s ease-in-out; {\'border: 2.5px solid #222222; box-shadow: 0 4px 12px rgba(0,0,0,0.15); transform: translateY(-2px);\' if is_selected else \'\'}">\n',
        '                        \n',
        '                        <!-- Status Icon with Enhanced Styling -->\n',
        '                        <div style="margin-right: 0.7rem; display: flex; align-items: center; justify-content: center; min-width: 24px;">\n',
        '                            {status_icon}\n',
        '                        </div>\n',
        '                        \n',
        '                        <!-- Invoice Details -->\n',
        '                        <div style="flex: 1; min-width: 0;">\n',
        '                            <div style="font-weight: 700; font-size: 1.05rem; color: #222; margin-bottom: 0.3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">\n',
        '                                {invoice_number}\n',
        '                            </div>\n',
        '                            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">\n',
        '                                {supplier}\n',
        '                            </div>\n',
        '                            <div style="font-size: 0.85rem; color: #888; margin-bottom: 0.5rem;">\n',
        '                                {date}\n',
        '                            </div>\n',
        '                            <div style="font-size: 1.1rem; font-weight: 700; color: #222;">\n',
        '                                {total}\n',
        '                            </div>\n',
        '                        </div>\n',
        '                        \n',
        '                        <!-- Status Badge -->\n',
        '                        <div style="margin-left: 0.5rem; text-align: right; min-width: 80px;">\n',
        '                            <div style="font-size: 0.8rem; color: {get_status_color(status)}; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">\n',
        '                                {status.replace(\'_\', \' \')}\n',
        '                            </div>\n',
        '                            {f\'<div style="font-size: 0.7rem; color: #999; margin-top: 0.2rem;">🔄 Processing</div>\' if status == \'processing\' else \'\'}\n',
        '                        </div>\n',
        '                        \n',
        '                        <!-- Selection Indicator -->\n',
        '                        {f\'<div style="position: absolute; top: 0; right: 0; width: 0; height: 0; border-left: 12px solid transparent; border-right: 12px solid #222222; border-top: 12px solid #222222;"></div>\' if is_selected else \'\'}\n',
        '                    </div>\n',
        '                \'\'\', unsafe_allow_html=True)\n',
        '                # Add keyboard navigation hint for first card\n',
        '                if idx == 0:\n',
        '                    st.markdown(\'\'\'\n',
        '                        <div style="font-size: 0.75rem; color: #999; text-align: center; margin: 0.5rem 0; padding: 0.3rem; background: #f8f9fa; border-radius: 4px;">\n',
        '                            💡 Use Tab to navigate, Enter to select • Arrow keys to move between invoices\n',
        '                        </div>\n',
        '                    \'\'\', unsafe_allow_html=True)\n',
        '        else:\n',
        '            # Enhanced empty state with helpful guidance\n',
        '            st.markdown(\'\'\'\n',
        '                <div style="text-align: center; padding: 3rem 1rem; color: #666;">\n',
        '                    <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>\n',
        '                    <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">\n',
        '                        No invoices uploaded yet\n',
        '                    </div>\n',
        '                    <div style="font-size: 0.95rem; line-height: 1.5; margin-bottom: 1.5rem;">\n',
        '                        Upload some invoices using the boxes above to get started.<br>\n',
        '                        The system will automatically process and display them here with real-time status updates.\n',
        '                    </div>\n',
        '                    <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem; font-size: 0.9rem; color: #666;">\n',
        '                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: #222;">📋 What happens next:</div>\n',
        '                        <ul style="text-align: left; margin: 0; padding-left: 1.2rem;">\n',
        '                            <li>Upload invoices and delivery notes</li>\n',
        '                            <li>System processes files with OCR</li>\n',
        '                            <li>Automatic discrepancy detection</li>\n',
        '                            <li>Real-time status updates</li>\n',
        '                        </ul>\n',
        '                    </div>\n',
        '                </div>\n',
        '            \'\'\', unsafe_allow_html=True)\n',
        '            \n',
        '    except Exception as e:\n',
        '        st.error(f"❌ Failed to load invoice list: {str(e)}")\n',
        '        \n',
        '        # Enhanced error state with retry option\n',
        '        st.markdown(\'\'\'\n',
        '            <div style="text-align: center; padding: 2rem 1rem; color: #666;">\n',
        '                <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>\n',
        '                <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #222;">\n',
        '                    Unable to load invoices\n',
        '                </div>\n',
        '                <div style="font-size: 0.9rem; line-height: 1.4; margin-bottom: 1rem;">\n',
        '                    There was an error loading the invoice list.<br>\n',
        '                    Please try refreshing the page or contact support.\n',
        '                </div>\n',
        '                <button onclick="location.reload()" style="background: #f1c232; color: #222; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-weight: 600;">\n',
        '                    🔄 Refresh Page\n',
        '                </button>\n',
        '            </div>\n',
        '        \'\'\', unsafe_allow_html=True)\n',
        '        \n',
        '        # Track error for debugging\n',
        '        if \'invoice_list_error_count\' not in st.session_state:\n',
        '            st.session_state.invoice_list_error_count = 0\n',
        '        st.session_state.invoice_list_error_count += 1\n'
    ]
    
    # Remove the orphaned lines
    for line in lines_to_remove:
        content = content.replace(line, '')
    
    # Write the fixed file
    with open('app/invoices_page.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed all indentation errors in invoices_page.py")

if __name__ == "__main__":
    fix_indentation_complete() 