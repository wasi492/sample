"""
app.py — All routes for the Sample Tracking System.
Flask application with server-rendered Jinja2 templates.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from database import init_db, seed_parameters, create_backup, get_all_samples, \
    get_next_sample_id, insert_sample, search_samples, get_sample, \
    get_all_parameters, get_sample_results, save_sample_results, \
    update_sample_status, soft_delete_sample, restore_sample as db_restore, \
    permanent_delete_sample, get_deleted_samples, add_parameter, \
    create_folder, get_all_folders, get_folder, get_samples_by_folder, \
    update_sample_folder, delete_folder
from report import generate_docx_report, generate_combined_docx_report
from export import generate_export

app = Flask(__name__)
app.secret_key = 'sample-tracker-secret-key'

# Track whether startup backup has been done (once per process)
_backup_done = False


@app.before_request
def before_request():
    """Run backup once on the first request after app startup."""
    global _backup_done
    if not _backup_done:
        create_backup()
        _backup_done = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """List all non-deleted samples."""
    samples = get_all_samples()
    return render_template('index.html', samples=samples)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """GET: show registration form. POST: create a new sample."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        received_from = request.form.get('received_from', '').strip()
        date_received = request.form.get('date_received', '').strip()
        folder_id_raw = request.form.get('folder_id', '').strip()
        folder_id = int(folder_id_raw) if folder_id_raw else None

        # Server-side validation: all fields required
        if not name or not received_from or not date_received:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        # Generate the next sequential Sample ID
        sample_id = get_next_sample_id()
        insert_sample(sample_id, name, received_from, date_received, folder_id)

        flash(f'Sample {sample_id} registered successfully.', 'success')
        return redirect(url_for('index'))

    folders = get_all_folders()
    return render_template('register.html', folders=folders)


@app.route('/search')
def search():
    """Search samples by ID, name, sender, or date."""
    query = request.args.get('q', None)
    results = None

    if query is not None:
        query = query.strip()
        if query:
            results = search_samples(query)
        else:
            results = []

    return render_template('search.html', query=query, results=results)


@app.route('/sample/<sample_id>')
def sample_detail(sample_id):
    """Show full detail for one sample, including test parameters form."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    parameters = get_all_parameters()
    results = get_sample_results(sample_id)
    folders = get_all_folders()

    # Look up the current folder name for display
    current_folder = None
    if sample['folder_id']:
        current_folder = get_folder(sample['folder_id'])

    # Build lookup dicts for the template to pre-fill saved results
    saved_ids = set()
    saved_results = {}
    saved_methods = {}
    for r in results:
        saved_ids.add(r['parameter_id'])
        saved_results[r['parameter_id']] = r['result']
        saved_methods[r['parameter_id']] = r['method']

    return render_template('sample.html',
                           sample=sample,
                           parameters=parameters,
                           saved_ids=saved_ids,
                           saved_results=saved_results,
                           saved_methods=saved_methods,
                           folders=folders,
                           current_folder=current_folder)


@app.route('/sample/<sample_id>/results', methods=['POST'])
def save_results(sample_id):
    """Save test parameter results (with method) for a sample."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    parameters = get_all_parameters()
    results_list = []

    for param in parameters:
        # Check if this parameter's checkbox was selected
        checkbox_key = f'param_{param["id"]}'
        result_key = f'result_{param["id"]}'
        method_key = f'method_{param["id"]}'

        if request.form.get(checkbox_key):
            result_value = request.form.get(result_key, '').strip()
            method_value = request.form.get(method_key, '').strip()
            if result_value:
                results_list.append((param['id'], result_value, method_value))

    save_sample_results(sample_id, results_list)
    flash('Test results saved successfully.', 'success')
    return redirect(url_for('sample_detail', sample_id=sample_id))


@app.route('/sample/<sample_id>/add_parameter', methods=['POST'])
def add_new_parameter(sample_id):
    """Add a brand-new test parameter to the master list from the sample detail page."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    param_name = request.form.get('new_param_name', '').strip()
    param_unit = request.form.get('new_param_unit', '').strip()

    if not param_name:
        flash('Parameter name is required.', 'error')
        return redirect(url_for('sample_detail', sample_id=sample_id))

    # Default unit to "—" if left blank
    if not param_unit:
        param_unit = '—'

    add_parameter(param_name, param_unit)
    flash(f'New parameter "{param_name}" added to the master list.', 'success')
    return redirect(url_for('sample_detail', sample_id=sample_id))


@app.route('/sample/<sample_id>/status', methods=['POST'])
def update_status(sample_id):
    """Toggle sample status between 'Under Testing' and 'Report Sent'."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    # Toggle: if currently Under Testing → Report Sent, and vice versa
    new_status = 'Report Sent' if sample['status'] == 'Under Testing' else 'Under Testing'
    update_sample_status(sample_id, new_status)

    flash(f'Status updated to "{new_status}".', 'success')
    return redirect(url_for('sample_detail', sample_id=sample_id))


@app.route('/sample/<sample_id>/report')
def download_report(sample_id):
    """Generate and download a Word (.docx) report for a sample."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    try:
        filepath = generate_docx_report(sample_id)
        return send_file(filepath, as_attachment=True,
                         download_name=f'{sample_id}_report.docx')
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('sample_detail', sample_id=sample_id))

@app.route('/sample/<sample_id>/delete', methods=['POST'])
def delete_sample(sample_id):
    """Soft delete a sample (set deleted = 1)."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    soft_delete_sample(sample_id)
    flash(f'Sample {sample_id} moved to Recently Deleted.', 'success')
    return redirect(url_for('index'))


@app.route('/deleted')
def deleted():
    """List all soft-deleted samples."""
    samples = get_deleted_samples()
    return render_template('deleted.html', samples=samples)


@app.route('/sample/<sample_id>/restore', methods=['POST'])
def restore_sample(sample_id):
    """Restore a soft-deleted sample."""
    db_restore(sample_id)
    flash(f'Sample {sample_id} restored.', 'success')
    return redirect(url_for('deleted'))


@app.route('/sample/<sample_id>/delete_permanent', methods=['POST'])
def permanent_delete(sample_id):
    """Permanently delete a sample. Irreversible."""
    permanent_delete_sample(sample_id)
    flash(f'Sample {sample_id} permanently deleted.', 'success')
    return redirect(url_for('deleted'))


# ---------------------------------------------------------------------------
# Folder routes
# ---------------------------------------------------------------------------

@app.route('/folders')
def folders_list():
    """List all folders."""
    folders = get_all_folders()
    return render_template('folders.html', folders=folders)


@app.route('/folders/new', methods=['POST'])
def folder_create():
    """Create a new folder."""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Folder name is required.', 'error')
        return redirect(url_for('folders_list'))

    try:
        create_folder(name)
        flash(f'Folder "{name}" created.', 'success')
    except Exception:
        flash(f'A folder named "{name}" already exists.', 'error')

    return redirect(url_for('folders_list'))


@app.route('/folders/<int:folder_id>')
def folder_detail(folder_id):
    """Show samples assigned to a specific folder."""
    folder = get_folder(folder_id)
    if not folder:
        flash('Folder not found.', 'error')
        return redirect(url_for('folders_list'))

    samples = get_samples_by_folder(folder_id)
    return render_template('folder_detail.html', folder=folder, samples=samples)


@app.route('/sample/<sample_id>/folder', methods=['POST'])
def change_sample_folder(sample_id):
    """Update which folder a sample belongs to."""
    sample = get_sample(sample_id)
    if not sample:
        flash('Sample not found.', 'error')
        return redirect(url_for('index'))

    folder_id_raw = request.form.get('folder_id', '').strip()
    folder_id = int(folder_id_raw) if folder_id_raw else None
    update_sample_folder(sample_id, folder_id)

    flash('Folder updated.', 'success')
    return redirect(url_for('sample_detail', sample_id=sample_id))


@app.route('/folders/<int:folder_id>/delete', methods=['POST'])
def folder_delete(folder_id):
    """Delete a folder. Samples in it are unassigned, not deleted."""
    folder = get_folder(folder_id)
    if not folder:
        flash('Folder not found.', 'error')
        return redirect(url_for('folders_list'))

    delete_folder(folder_id)
    flash(f'Folder "{folder["name"]}" deleted. Its samples have been unassigned.', 'success')
    return redirect(url_for('folders_list'))


@app.route('/reports/combined', methods=['POST'])
def combined_report():
    """Generate a combined Word report for multiple selected samples."""
    sample_ids = request.form.getlist('sample_ids')

    if not sample_ids:
        flash('No samples selected. Please select at least one sample.', 'error')
        return redirect(url_for('index'))

    try:
        filepath = generate_combined_docx_report(sample_ids)
        return send_file(filepath, as_attachment=True,
                         download_name='combined_report.docx')
    except Exception as e:
        flash(f'Error generating combined report: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/export')
def export_excel():
    """Generate and download an Excel (.xlsx) export of all samples."""
    try:
        filepath = generate_export()
        return send_file(filepath, as_attachment=True,
                         download_name='samples_export.xlsx')
    except Exception as e:
        flash(f'Error generating export: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/backup')
def download_backup():
    """Download the current live lab.db file as a backup."""
    from database import DB_PATH
    if not os.path.exists(DB_PATH):
        flash('Database file not found.', 'error')
        return redirect(url_for('index'))

    return send_file(DB_PATH, as_attachment=True,
                     download_name='lab_backup.db')


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    seed_parameters()
    app.run(debug=True, port=5000)
