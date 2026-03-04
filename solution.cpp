#include <iostream>
#include <vector>
#include <string>

using namespace std;

void solve() {
    int n, s;
    long long k;
    if (!(cin >> n >> s >> k)) return;
    
    string dirs;
    cin >> dirs;
    
    vector<int> L(n + 1), R(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> L[i] >> R[i];
    }
    
    if (k == 0) {
        cout << s << "\n";
        return;
    }
    
    vector<int> path;
    vector<int> vis(n + 1, -1);
    
    int current = s;
    vis[current] = 0;
    path.push_back(current);
    
    long long step = 0;
    while (step < k) {
        step++;
        int next_node;
        if (dirs[current - 1] == 'L') {
            next_node = L[current];
        } else {
            next_node = R[current];
        }
        
        if (step == k) {
            cout << next_node << "\n";
            return;
        }
        
        if (vis[next_node] != -1) {
            long long cycle_start = vis[next_node];
            long long cycle_len = step - cycle_start;
            long long remaining = k - step;
            long long final_idx = cycle_start + (remaining % cycle_len);
            cout << path[final_idx] << "\n";
            return;
        }
        
        vis[next_node] = step;
        path.push_back(next_node);
        current = next_node;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}
