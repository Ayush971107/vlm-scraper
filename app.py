from flask import Flask, render_template, send_file, abort
import pandas as pd
import os
import sys
from datetime import datetime

app = Flask(__name__)

def load_analysis_data(target_repo=None):
    """
    Load analysis data from repository directories.
    If target_repo is specified, only load data from that repository.
    """
    all_data = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find directories that contain repo data
    if target_repo:
        # If specific repo is requested, only look in that folder
        repo_dir = os.path.join(current_dir, target_repo)
        if os.path.isdir(repo_dir):
            excel_files = [f for f in os.listdir(repo_dir) if f.endswith('.xlsx')]
            for excel_file in excel_files:
                try:
                    file_path = os.path.join(repo_dir, excel_file)
                    df = pd.read_excel(file_path, engine='openpyxl')
                    df['repo_directory'] = repo_dir
                    all_data.append(df)
                    print(f"Loaded data from: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
        else:
            print(f"Repository directory '{target_repo}' not found")
    else:
        # Otherwise look through all potential repo directories
        for item in os.listdir(current_dir):
            repo_dir = os.path.join(current_dir, item)
            if os.path.isdir(repo_dir) and '_' in item:  # Potential repo directory
                excel_files = [f for f in os.listdir(repo_dir) if f.endswith('.xlsx')]
                for excel_file in excel_files:
                    try:
                        file_path = os.path.join(repo_dir, excel_file)
                        df = pd.read_excel(file_path, engine='openpyxl')
                        df['repo_directory'] = repo_dir
                        all_data.append(df)
                        print(f"Loaded data from: {file_path}")
                    except Exception as e:
                        print(f"Error reading {file_path}: {str(e)}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

@app.route('/download/<path:repo_name>/<path:filename>')
def download_file(repo_name, filename):
    """
    Handle downloading of snapshot files from the repository-specific snapshot directory.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_dir = os.path.join(current_dir, repo_name)
        file_path = os.path.join(repo_dir, 'snapshots', filename)
        
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
        else:
            print(f"File not found: {file_path}")
            abort(404)
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        abort(500)

@app.route('/')
def index():
    # Get target repo from command line if specified
    target_repo = None
    if len(sys.argv) > 1:
        target_repo = sys.argv[1]
        print(f"Displaying data for repository: {target_repo}")
    
    df = load_analysis_data(target_repo)
    if df.empty:
        return render_template('no_data.html')
    
    # Group by repository
    repos = df['Repo Identifier'].unique()
    repo_data = {}
    
    for repo in repos:
        repo_df = df[df['Repo Identifier'] == repo]
        commits = []
        
        # Get the repo directory from the first row
        repo_directory = repo_df.iloc[0]['repo_directory']
        repo_dir_name = os.path.basename(repo_directory)
        
        for _, row in repo_df.iterrows():
            # Get just the filename from the full path
            pre_commit = os.path.basename(str(row['Code Pre Commit'])) if str(row['Code Pre Commit']) != "N/A" else "N/A"
            post_commit = os.path.basename(str(row['Code Post Commit']))
            
            commit = {
                'index': row['Commit Index'],
                'sha': row['Commit SHA'],
                'description': row['AI Description'],
                'has_visual_changes': row['AI Description'].lower() != 'no visual changes',
                'pre_commit': pre_commit,
                'post_commit': post_commit,
                'repo_dir_name': repo_dir_name,
                'timestamp': datetime.now().strftime('%Y-%m-%d')
            }
            commits.append(commit)
        
        repo_data[repo] = {
            'commits': commits,
            'total_commits': len(commits),
            'visual_changes': sum(1 for c in commits if c['has_visual_changes'])
        }
    
    return render_template('index.html', repo_data=repo_data)

if __name__ == '__main__':
    app.run(debug=True)

