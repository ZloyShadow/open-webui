<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';

  interface Policy {
    user_id: number;
    name: string;
    is_active: boolean;
    mode: 'audit' | 'block';
    notify_email: boolean;
    notify_telegram: boolean;
    notify_slack: boolean;
    email_recipients: string[];
    telegram_chats: string[];
    slack_webhooks: string[];
    created_at: string;
    updated_at: string;
  }

  interface StopWord {
    id: number;
    word: string;
    description: string | null;
    check_type: 'exact' | 'contains' | 'regex';
    apply_to_chat: boolean;
    apply_to_api: boolean;
    apply_to_documents: boolean;
    is_active: boolean;
    created_at: string;
  }

  interface Alert {
    id: number;
    user_id: number;
    stop_word: string | null;
    trigger_content: string;
    context_type: 'chat' | 'api' | 'document';
    action_taken: 'logged' | 'blocked';
    created_at: string;
  }

  let userId = $page.data.userId || '';
  let policy: Policy | null = null;
  let stopWords: StopWord[] = [];
  let alerts: Alert[] = [];
  let loading = true;
  let saving = false;
  let activeTab = 'policy';

  // Form data for policy
  let policyForm = {
    name: 'Default Policy',
    mode: 'audit' as 'audit' | 'block',
    notify_email: false,
    notify_telegram: false,
    notify_slack: false,
    email_recipients: '',
    telegram_chats: '',
    slack_webhooks: ''
  };

  // Form data for new stop word
  let stopWordForm = {
    word: '',
    description: '',
    check_type: 'contains' as 'exact' | 'contains' | 'regex',
    apply_to_chat: true,
    apply_to_api: true,
    apply_to_documents: true,
    is_active: true
  };

  onMount(async () => {
    if (userId) {
      await loadPolicy();
      await loadStopWords();
      await loadAlerts();
    }
    loading = false;
  });

  async function loadPolicy() {
    try {
      const res = await fetch(`/api/security/policies/${userId}`);
      if (res.ok) {
        policy = await res.json();
        if (policy) {
          policyForm = {
            name: policy.name,
            mode: policy.mode,
            notify_email: policy.notify_email,
            notify_telegram: policy.notify_telegram,
            notify_slack: policy.notify_slack,
            email_recipients: policy.email_recipients.join(', '),
            telegram_chats: policy.telegram_chats.join(', '),
            slack_webhooks: policy.slack_webhooks.join(', ')
          };
        }
      }
    } catch (error) {
      console.error('Failed to load policy:', error);
    }
  }

  async function loadStopWords() {
    try {
      const res = await fetch(`/api/security/policies/${userId}/stop-words`);
      if (res.ok) {
        stopWords = await res.json();
      }
    } catch (error) {
      console.error('Failed to load stop words:', error);
    }
  }

  async function loadAlerts() {
    try {
      const res = await fetch(`/api/security/alerts?user_id=${userId}&limit=50`);
      if (res.ok) {
        alerts = await res.json();
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
    }
  }

  async function savePolicy() {
    saving = true;
    try {
      const payload = {
        ...policyForm,
        email_recipients: policyForm.email_recipients.split(',').map(s => s.trim()).filter(Boolean),
        telegram_chats: policyForm.telegram_chats.split(',').map(s => s.trim()).filter(Boolean),
        slack_webhooks: policyForm.slack_webhooks.split(',').map(s => s.trim()).filter(Boolean)
      };

      const res = await fetch(`/api/security/policies/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        await loadPolicy();
        alert('Policy saved successfully');
      } else {
        alert('Failed to save policy');
      }
    } catch (error) {
      console.error('Failed to save policy:', error);
      alert('Error saving policy');
    } finally {
      saving = false;
    }
  }

  async function addStopWord() {
    if (!stopWordForm.word.trim()) {
      alert('Please enter a stop word');
      return;
    }

    try {
      const res = await fetch(`/api/security/policies/${userId}/stop-words`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stopWordForm)
      });

      if (res.ok) {
        stopWordForm.word = '';
        stopWordForm.description = '';
        await loadStopWords();
        alert('Stop word added successfully');
      } else {
        alert('Failed to add stop word');
      }
    } catch (error) {
      console.error('Failed to add stop word:', error);
      alert('Error adding stop word');
    }
  }

  async function deleteStopWord(id: number) {
    if (!confirm('Are you sure you want to delete this stop word?')) {
      return;
    }

    try {
      const res = await fetch(`/api/security/stop-words/${id}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        await loadStopWords();
        alert('Stop word deleted successfully');
      } else {
        alert('Failed to delete stop word');
      }
    } catch (error) {
      console.error('Failed to delete stop word:', error);
      alert('Error deleting stop word');
    }
  }
</script>

<svelte:head>
  <title>Security Policies - Admin</title>
</svelte:head>

<div class="container mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6" data-testid="security-title">Security Policies Management</h1>

  {#if loading}
    <div class="flex justify-center items-center py-12" data-testid="loading-spinner">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  {:else}
    <!-- User ID Input -->
    <div class="mb-6 bg-white rounded-lg shadow p-4" data-testid="user-id-section">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        User ID
      </label>
      <div class="flex gap-2">
        <input
          type="number"
          bind:value={userId}
          data-testid="user-id-input"
          class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter user ID"
        />
        <button
          on:click={() => { loading = true; loadPolicy(); loadStopWords(); loadAlerts(); loading = false; }}
          data-testid="load-button"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
        >
          Load
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="mb-6 border-b border-gray-200" data-testid="tabs-container">
      <nav class="-mb-px flex space-x-8">
        <button
          class:active={activeTab === 'policy'}
          class="py-4 px-1 border-b-2 font-medium text-sm"
          class:border-blue-500={activeTab === 'policy'}
          class:text-blue-600={activeTab === 'policy'}
          class:border-transparent={activeTab !== 'policy'}
          class:text-gray-500={activeTab !== 'policy'}
          on:click={() => activeTab = 'policy'}
          data-testid="tab-policy"
        >
          Policy Settings
        </button>
        <button
          class:active={activeTab === 'stopwords'}
          class="py-4 px-1 border-b-2 font-medium text-sm"
          class:border-blue-500={activeTab === 'stopwords'}
          class:text-blue-600={activeTab === 'stopwords'}
          class:border-transparent={activeTab !== 'stopwords'}
          class:text-gray-500={activeTab !== 'stopwords'}
          on:click={() => activeTab = 'stopwords'}
          data-testid="tab-stopwords"
        >
          Stop Words ({stopWords.length})
        </button>
        <button
          class:active={activeTab === 'alerts'}
          class="py-4 px-1 border-b-2 font-medium text-sm"
          class:border-blue-500={activeTab === 'alerts'}
          class:text-blue-600={activeTab === 'alerts'}
          class:border-transparent={activeTab !== 'alerts'}
          class:text-gray-500={activeTab !== 'alerts'}
          on:click={() => activeTab = 'alerts'}
          data-testid="tab-alerts"
        >
          Security Alerts ({alerts.length})
        </button>
      </nav>
    </div>

    <!-- Policy Tab -->
    {#if activeTab === 'policy'}
      <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">Policy Configuration</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Policy Name
            </label>
            <input
              type="text"
              bind:value={policyForm.name}
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Mode
            </label>
            <select
              bind:value={policyForm.mode}
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="audit">Audit (Log only, don't block)</option>
              <option value="block">Block (Block requests and notify)</option>
            </select>
          </div>

          <div class="border-t pt-4">
            <h3 class="text-lg font-medium mb-3">Notification Channels</h3>
            
            <div class="space-y-3">
              <label class="flex items-center">
                <input
                  type="checkbox"
                  bind:checked={policyForm.notify_email}
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">Enable Email Notifications</span>
              </label>
              
              {#if policyForm.notify_email}
                <div class="ml-6">
                  <label class="block text-sm text-gray-600 mb-1">Email Recipients (comma-separated)</label>
                  <input
                    type="text"
                    bind:value={policyForm.email_recipients}
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="admin@example.com, security@example.com"
                  />
                </div>
              {/if}

              <label class="flex items-center">
                <input
                  type="checkbox"
                  bind:checked={policyForm.notify_telegram}
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">Enable Telegram Notifications</span>
              </label>
              
              {#if policyForm.notify_telegram}
                <div class="ml-6">
                  <label class="block text-sm text-gray-600 mb-1">Telegram Chat IDs (comma-separated)</label>
                  <input
                    type="text"
                    bind:value={policyForm.telegram_chats}
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="-1001234567890, -987654321"
                  />
                </div>
              {/if}

              <label class="flex items-center">
                <input
                  type="checkbox"
                  bind:checked={policyForm.notify_slack}
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">Enable Slack Notifications</span>
              </label>
              
              {#if policyForm.notify_slack}
                <div class="ml-6">
                  <label class="block text-sm text-gray-600 mb-1">Slack Webhook URLs (comma-separated)</label>
                  <input
                    type="text"
                    bind:value={policyForm.slack_webhooks}
                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="https://hooks.slack.com/..."
                  />
                </div>
              {/if}
            </div>
          </div>

          <div class="pt-4">
            <button
              on:click={savePolicy}
              disabled={saving}
              class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50"
            >
              {#if saving}Saving...{:else}Save Policy{/if}
            </button>
          </div>
        </div>
      </div>
    {/if}

    <!-- Stop Words Tab -->
    {#if activeTab === 'stopwords'}
      <div class="space-y-6" data-testid="stopwords-section">
        <!-- Add Stop Word Form -->
        <div class="bg-white rounded-lg shadow p-6" data-testid="add-stopword-form">
          <h2 class="text-xl font-semibold mb-4" data-testid="stopwords-title">Add Stop Word</h2>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Word/Pattern *
              </label>
              <input
                type="text"
                bind:value={stopWordForm.word}
                data-testid="stopword-word-input"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter stop word or regex pattern"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Match Type
              </label>
              <select
                bind:value={stopWordForm.check_type}
                data-testid="stopword-type-select"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="contains">Contains</option>
                <option value="exact">Exact Match</option>
                <option value="regex">Regular Expression</option>
              </select>
            </div>

            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                bind:value={stopWordForm.description}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional description"
              />
            </div>

            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Apply To
              </label>
              <div class="flex space-x-6">
                <label class="flex items-center">
                  <input
                    type="checkbox"
                    bind:checked={stopWordForm.apply_to_chat}
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Chat</span>
                </label>
                <label class="flex items-center">
                  <input
                    type="checkbox"
                    bind:checked={stopWordForm.apply_to_api}
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">API</span>
                </label>
                <label class="flex items-center">
                  <input
                    type="checkbox"
                    bind:checked={stopWordForm.apply_to_documents}
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Documents</span>
                </label>
              </div>
            </div>
          </div>

          <div class="mt-4">
            <button
              on:click={addStopWord}
              class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition"
            >
              Add Stop Word
            </button>
          </div>
        </div>

        <!-- Stop Words List -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-6 border-b">
            <h2 class="text-xl font-semibold">Current Stop Words</h2>
          </div>
          
          {#if stopWords.length === 0}
            <div class="p-6 text-center text-gray-500">
              No stop words configured yet.
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Word</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Apply To</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {#each stopWords as word}
                    <tr>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">{word.word}</div>
                        {#if word.description}
                          <div class="text-sm text-gray-500">{word.description}</div>
                        {/if}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                          {word.check_type}
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex space-x-2">
                          {#if word.apply_to_chat}
                            <span class="px-2 py-1 bg-gray-100 text-xs rounded">Chat</span>
                          {/if}
                          {#if word.apply_to_api}
                            <span class="px-2 py-1 bg-gray-100 text-xs rounded">API</span>
                          {/if}
                          {#if word.apply_to_documents}
                            <span class="px-2 py-1 bg-gray-100 text-xs rounded">Docs</span>
                          {/if}
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                              class:bg-green-100={word.is_active}
                              class:text-green-800={word.is_active}
                              class:bg-red-100={!word.is_active}
                              class:text-red-800={!word.is_active}>
                          {#if word.is_active}Active{:else}Inactive{/if}
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          on:click={() => deleteStopWord(word.id)}
                          class="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Alerts Tab -->
    {#if activeTab === 'alerts'}
      <div class="bg-white rounded-lg shadow" data-testid="alerts-section">
        <div class="p-6 border-b">
          <h2 class="text-xl font-semibold" data-testid="alerts-title">Security Alerts History</h2>
          <p class="text-sm text-gray-500 mt-1">Last 50 alerts for this user</p>
        </div>
        
        {#if alerts.length === 0}
          <div class="p-6 text-center text-gray-500" data-testid="no-alerts-message">
            No security alerts recorded yet.
          </div>
        {:else}
          <div class="overflow-x-auto" data-testid="alerts-table-container">
            <table class="min-w-full divide-y divide-gray-200" data-testid="alerts-table">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trigger</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Context</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Content Preview</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each alerts as alert}
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      {#if alert.stop_word}
                        <span class="px-2 py-1 bg-red-100 text-red-800 text-xs rounded font-medium">
                          {alert.stop_word}
                        </span>
                      {:else}
                        <span class="text-gray-400">Unknown</span>
                      {/if}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded capitalize">
                        {alert.context_type}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="px-2 py-1 text-xs rounded font-medium"
                            class:bg-yellow-100={alert.action_taken === 'logged'}
                            class:text-yellow-800={alert.action_taken === 'logged'}
                            class:bg-red-100={alert.action_taken === 'blocked'}
                            class:text-red-800={alert.action_taken === 'blocked'}>
                        {alert.action_taken === 'logged' ? '📝 Logged' : '🚫 Blocked'}
                      </span>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500 max-w-md truncate">
                      {alert.trigger_content.slice(0, 100)}{alert.trigger_content.length > 100 ? '...' : ''}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .container {
    max-width: 1200px;
  }
  
  button.active {
    border-bottom: 2px solid #3b82f6;
    color: #1d4ed8;
  }
</style>
