type Extension = {
    extension_id: number;
    name: string;
    local_path: string;
    metadata: {
        installed_version: string;
        git_repo_url: string;
    };
};
