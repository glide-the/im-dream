// [Sync] 2026-09-27: localize task-session source navigation and created-task lists.
// [Sync] 2026-09-29: localize per-user-message turn navigation, previews, loading, and locate feedback.
// [Sync] 2026-09-27: localize consolidated Chat information and server-reported task states.
// [Sync] 2026-09-28: localize completed task status and durable result notification states.
// [Sync] 2026-09-28: localize scheduled Chat cards, revision conflicts and date-query recovery.
// [Sync] 2026-09-29: localize the reviewed date workspace, task state hierarchy, conflict recovery, and accessibility labels.
// [Sync] 2026-09-29: localize date-qualified floating task/diary card headings and plain card counts.
// [Sync] 2026-09-29: localize task composer/result/editor flows and Chat scheduled-task marker/detail surfaces.
// [Sync] 2026-09-27: clarify queue-unavailable feedback and label read-only status refresh.
// [Sync] 2026-09-28: explain uncertain dispatched inputs separately from retained unsent drafts.
// [Sync] 2026-09-26: localize queued input status, guidance and failure feedback.
// [Input] User locale and product-facing translation keys.
// [Output] English and Simplified Chinese UI copy for Ink & Memory surfaces.
// [Pos] Frontend i18next resource registry.
// [Sync] 2026-09-13: add explicit file-download and report-preview close labels.
// [Sync] 2026-09-02: add lazy historical process loading and failure copy.
// [Sync] 2026-08-14: add actor-owned publication and system-default sharing copy.
// [Sync] 2026-08-15: add the localized More disclosure for restored legacy navigation.
// [Sync] 2026-08-16: add the PDF-led Deck home, create menu, enabled strip, counted filters,
//                    flat-list status, refresh, pagination, and lightweight-detail copy.
// [Sync] 2026-08-16: remove obsolete Deck page-heading and use/create-mode copy.
// [Sync] 2026-08-16: remove Deck market/workbench copy and add lightweight details,
//                    pagination, and recoverable management feedback.
// [Sync] 2026-08-16: restore full popup-maintenance confirmations and recoverable
//                    Agent mutation feedback from the pre-01a00576 baseline.
// [Sync] 2026-08-17: explain the published-clean Deck-home empty state.
// [Sync] 2026-08-17: add Work-related Chat history cleanup and deletion guidance copy.
// [Sync] 2026-08-29: add connector partial-availability labels and remove unavailable platform claims from empty states.
// [Sync] 2026-08-17: localize the Story Workspace Settings shell and render Work/工作台 per locale.
// [Sync] 2026-08-17: label Available/System Deck launcher groups and default-visible system Decks.
// [Sync] 2026-08-22: add localized Workspace URI preview/download and full-size image dialog states under the existing Chat namespace.
// [Sync] 2026-08-23: add the inert Workspace-image fallback used when a protected asset cannot be embedded in Chat export.
// [Sync] 2026-08-23: localize the shared Mermaid/Workspace enlarge, download, close, and zoom controls.
// [Sync] 2026-08-29: add truthful Editor write failure and retained-input recovery copy.
// [Sync] 2026-08-31: add safe structured Chat turn-error and Thread reload copy.
// [Sync] 2026-08-31: remove the unused daily-picture generation status copy.
// [Sync] 2026-09-01: add manual Writing suggestion trigger, lifecycle, and recovery copy.
// [Sync] 2026-09-01: label visible Dream workbench auto-repair user messages.
// [Sync] 2026-09-02: localize historical assistant process disclosure and
//                    paged-history loading/recovery states.
// [Sync] 2026-09-04: distinguish a saved Agent reply with incomplete Dream
//                    synchronization from a message that was not processed.
// [Sync] 2026-09-06: localize MCP App interactive-view lifecycle and recovery controls.
// [Sync] 2026-09-17: add safe Chat recovery copy for an exhausted subscription-period Token allowance.
// [Sync] 2026-09-18: align the visible Chat shortcut hint with Enter send and Shift+Enter newline behavior.

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const LANGUAGE_STORAGE_KEY = 'ink-language';

const resources = {
  en: {
    translation: {
      nav: {
        writing: 'Writing',
        timeline: 'Timeline',
        analysis: 'Reflections',
        decks: 'Decks',
        connector: 'Connector',
        dream: 'Dream',
        chat: 'Chat',
        more: 'More',
        friends: 'Friends',
        settings: 'Settings'
      },
      writingSuggestion: {
        goDeeper: 'Go deeper',
        loading: 'Going deeper…',
        refresh: 'Refresh',
        retry: 'Retry',
        regionLabel: 'Writing suggestion',
        threadTitle: 'Writing suggestions',
        failed: 'The suggestion was interrupted. Your writing is unchanged.',
        unavailable: 'Suggestions are unavailable right now.',
        errors: {
          threadCreate: 'The suggestion conversation could not be started. Try again.',
          threadPersist: 'The suggestion conversation could not be saved. Try again.',
          interrupted: 'The suggestion was interrupted. Your writing is unchanged.'
        }
      },
      settings: {
        heading: 'The Voice Council',
        subheading: 'Configure the inner voices that annotate everything you write.',
        tabs: {
          voices: '🎭 Voices',
          meta: '📜 Meta Prompt',
          states: '💭 User States'
        },
        language: {
          title: 'Interface Language',
          description: 'Choose which language the UI uses while your writing stays untouched.',
          placeholder: 'Select a language',
          preview: 'Changes apply immediately to menus, buttons, and helper copy.',
          options: {
            en: 'English',
            zh: '中文 (Chinese)'
          }
        },
        workspace: {
          aria: {
            categories: 'Settings categories',
            navigation: 'Settings categories navigation',
            content: 'Settings content'
          },
          backToApp: 'Back to app',
          personal: 'Personal',
          search: {
            label: 'Search settings',
            placeholder: 'Search settings…',
            noResults: 'No matching settings'
          },
          navigation: {
            general: 'General',
            subscription: 'Subscription',
            work: 'Work',
            model: 'AI models',
            about: 'About'
          },
          general: {
            description: 'Adjust the interface language and workspace display preferences.'
          },
          languageLabel: 'Language',
          theme: {
            label: 'Appearance',
            description: 'Choose the appearance of the workspace.',
            options: {
              light: 'Light',
              system: 'System',
              dark: 'Dark'
            }
          },
          energy: {
            label: 'Energy Bar',
            description: 'Show the energy progress bar in the bottom stats line.',
            toggleLabel: 'Toggle energy bar'
          },
          work: {
            title: 'Work',
            description: 'Manage the Decks, resource links, and plugins available in your creative workspace.',
            tabsLabel: 'Work management categories',
            tabs: {
              deck: 'Deck',
              resources: 'Resource links',
              plugins: 'Plugins'
            }
          },
          resourceDetail: {
            title: 'Resource connection',
            description: 'Manage an individual resource connection.'
          },
          model: {
            title: 'AI model configuration',
            description: 'Configure the models and runtime policies used by the creative workspace.'
          },
          about: {
            title: 'About',
            description: 'Information about the Ink & Memory workspace.'
          }
        }
      },
      analysis: {
        title: 'Reflections',
        subtitle: 'Patterns and insights woven through your words',
        backButton: 'Back',
        backTitle: 'Back to Dashboard',
        stats: {
          days: 'Days',
          entries: 'Entries',
          words: 'Words'
        },
        pastReflections: 'Past Reflections',
        report: {
          latest: 'Latest',
          patternCount: '{{count}} patterns'
        },
        actions: {
          generate: 'Generate New Analysis',
          generating: 'Reflecting...'
        },
        empty: {
          title: 'Your story awaits analysis',
          description: 'Begin the journey to discover the patterns, themes, and essence woven through your words'
        },
        papers: {
          echoes: { title: 'Recurring Themes', subtitle: 'Echoes' },
          traits: { title: 'Character Traits', subtitle: 'Personality' },
          patterns: { title: 'Behavioral Patterns', subtitle: 'Habits' }
        },
        statsLabels: {
          daysCount_one: '{{count}} day',
          daysCount_other: '{{count}} days',
          entriesCount_one: '{{count}} entry',
          entriesCount_other: '{{count}} entries',
          wordsCount: '{{value}} words'
        },
        reportCounts: {
          echoes_one: '{{count}} echo',
          echoes_other: '{{count}} echoes',
          traits_one: '{{count}} trait',
          traits_other: '{{count}} traits',
          patterns_one: '{{count}} pattern',
          patterns_other: '{{count}} patterns'
        }
      },
      deck: {
        loading: 'Loading Decks…',
        actions: {
          retry: 'Retry',
          create: 'Create Deck',
          createMenu: 'Create',
          creating: 'Creating Deck…',
          sync: 'Sync with Original',
          delete: 'Delete Deck',
          edit: 'Edit',
          inspect: 'Inspect template',
          fork: 'Fork',
          enable: 'Enable',
          disable: 'Disable',
          refresh: 'Refresh',
          refreshing: 'Refreshing…',
          clearFilters: 'Clear filters',
          more: 'More actions for {{deck}}',
          relatedConversations: 'Related conversations',
          enableDeck: 'Enable {{deck}}',
          disableDeck: 'Disable {{deck}}'
        },
        defaults: {
          newName: 'New Deck',
          newDescription: 'Describe your deck here'
        },
        home: {
          sectionLabel: 'Decks',
          title: 'Decks',
          description: 'Manage the Decks you use with Chat and Dream',
          launchDescription: 'Open an available Deck; manage drafts and other Decks in Settings',
          enabledTitle: 'Installed',
          enabledEmpty: 'No Deck is available.',
          availableEmpty: 'No Deck is available on this page.',
          allTitle: 'All Decks',
          launchCatalogTitle: 'Deck catalog',
          availableTitle: 'Available Decks',
          availableListTitle: 'Available Decks',
          availableListLabel: 'User-created available Decks',
          availableListEmpty: 'No user-created Deck is enabled with a published clean version.',
          systemListTitle: 'System Decks',
          systemListLabel: 'System built-in Decks',
          systemListEmpty: 'No system Deck is available.',
          launchSearchLabel: 'Search available Decks',
          launchListLabel: 'Available Deck list',
          openDeck: 'Open {{deck}}',
          systemDeckLabel: 'System built-in Deck {{deck}}',
          openSettings: 'Open Deck settings'
        },
        labels: {
          system: 'System',
          systemBuiltIn: 'System built-in',
          contentVersion: 'Content v{{version}}',
          noDescription: 'No description',
          voiceCount: '{{count}} voices',
          agentCount: '{{count}} Agents',
          anonymous: 'Anonymous',
          enabled: 'Enabled',
          disabled: 'Disabled',
          updateUnknown: 'Not recorded',
          agentType: {
            chat: 'Chat Agent',
            dream: 'Dream Agent'
          }
        },
        preview: {
          back: 'Back to Decks',
          tryNow: 'Try now',
          launchingDream: 'Starting Dream…',
          launchDreamFailed: 'Dream could not be started. Your Deck selection is unchanged; try again.',
          examples: 'Deck preview examples',
          defaultDescription: '{{deck}} is ready for Chat and Dream work.',
          agentsTitle: 'Agents {{count}}',
          noAgents: 'No Agent is configured for this Deck.',
          infoTitle: 'Information',
          infoDeveloper: 'Developer',
          systemDeveloper: 'Ink & Memory',
          userDeveloper: 'You',
          infoType: 'Category',
          infoVersion: 'Version',
          infoRuntime: 'Runtime',
          infoUpdated: 'Updated',
          editDeck: 'Edit Deck {{deck}}'
        },
        creator: {
          searchLabel: 'Search managed Decks',
          searchPlaceholder: 'Search name or description',
          agentTypeFilter: 'Filter by Agent type',
          agentTypeTabs: {
            all: 'All',
            chat: 'Chat',
            dream: 'Dream'
          },
          statusFilter: 'Filter by enabled state',
          statusAll: 'All states',
          empty: 'No managed Decks yet. Create one to begin.',
          noResults: 'No Deck matches these filters.',
          listLabel: 'Deck settings'
        },
        pagination: {
          ariaLabel: 'Deck list pages',
          previous: 'Previous',
          next: 'Next',
          summary: 'Page {{page}} of {{pages}}'
        },
        related: {
          title: 'Related conversations',
          description: 'This Deck stays protected while Chat conversations still use it. Review the same history previews shown in Chat and delete only the conversations you no longer need.',
          loading: 'Loading related conversations…',
          loadFailed: 'Related conversations could not be loaded.',
          deleteFailed: 'The conversation could not be deleted.',
          emptyTitle: 'No related conversations',
          emptyDescription: 'Chat history no longer blocks this Deck from being deleted.',
          listLabel: 'Related Chat conversations',
          confirmDelete: 'Delete “{{title}}”? This permanently removes its Chat history.',
          deleteConversation: 'Delete conversation {{title}}',
          delete: 'Delete',
          deleting: 'Deleting…',
          loadMore: 'Load more',
          loadingMore: 'Loading…',
          deleteHint: 'Delete every related conversation before deleting this Deck.',
          unknownHint: 'Retry loading related conversations before deleting this Deck.',
          readyHint: 'All related conversations are cleared. You can now retry Deck deletion.',
          deleteDeck: 'Delete Deck',
          close: 'Close'
        },
        details: {
          createTitle: 'Create Deck',
          editTitle: 'Edit Deck',
          inspectTitle: 'Deck details',
          name: 'Deck name',
          description: 'Description',
          icon: 'Icon',
          color: 'Color',
          defaultVisual: 'Use default',
          enableHint: 'Enable or disable this Deck from the management list.',
          nameRequired: 'Enter a Deck name.',
          saveFailed: 'Deck could not be saved. Try again.',
          cancel: 'Cancel',
          close: 'Close',
          save: 'Save',
          saving: 'Saving…'
        },
        confirm: {
          delete: 'Delete this deck and all its voices?',
          deleteAgent: 'Delete this Agent?',
          sync: 'Sync with original template? This will overwrite any changes you made to this deck.'
        },
        messages: {
          loadFailed: 'Decks could not be loaded.',
          createFailed: 'Deck could not be created.',
          createAgentFailed: 'Agent could not be created.',
          updateFailed: 'Deck could not be updated.',
          updateAgentFailed: 'Agent could not be updated.',
          toggleFailed: 'Deck status could not be changed.',
          forkFailed: 'Deck copy could not be created.',
          deleteFailed: 'Deck could not be deleted.',
          deleteAgentFailed: 'Agent could not be deleted.',
          syncFailed: 'Deck could not be synchronized.'
        }
      },
      timeline: {
        today: 'Today',
        entryCount_one: '{{count}} entry',
        entryCount_other: '{{count}} entries',
        friendSelector: {
          label: 'View Timeline',
          placeholder: 'Choose a friend',
          none: 'No friend selected',
          loading: 'Loading friends...',
          error: 'Could not load friends',
          button: 'Timeline settings',
          summarySolo: 'Personal timeline only',
          summaryWithFriend: 'Comparing with {{name}}',
          searchPlaceholder: 'Search friends',
          noFriends: 'You have no friends yet.',
          noMatches: 'No matches found',
          close: 'Close',
          personal: 'You',
          more: 'More',
          selfOnlyTitle: 'Just you today',
          selfOnlyHint: 'Pick a friend badge on the right to pull in their timeline beside yours.',
          friendEmptyTitle: 'No timeline yet',
          friendEmptyHint: 'This friend has not shared anything for these recent days.'
        },
        friendTimeline: {
          loading: 'Loading friend timeline...',
          empty: 'This friend has no entries yet.',
          error: 'Unable to load friend timeline.',
          readOnly: "Friend reflections open in read-only mode. You're just viewing their day.",
          readOnlyShort: 'Friend timeline preview'
        }
      },
      calendar: {
        title: 'Calendar',
        subtitle: 'Select a day to revisit your entries',
        empty: 'No entries yet. Start writing to fill this calendar.',
        untitled: 'Untitled',
        monthCalendarLabel: 'Monthly diary calendar',
        deleteConfirm: 'Delete this entry?',
        entriesLabel_one: '{{count}} entry',
        entriesLabel_other: '{{count}} entries',
        currentEntryLabel: 'Current note',
        openButton: 'Open',
        deleteButton: 'Delete',
        close: 'Close',
        prev: '← Prev',
        next: 'Next →',
        noEntriesForDate: 'No entries for this date',
        todayLabel: 'Today',
        loadError: 'Unable to open this entry.',
        deleteError: 'Failed to delete entry',
        diarySectionTitle: 'Diary',
        diarySectionTitleForDate: 'Diary · {{date}}',
        diaryCount_one: 'Diary {{count}}',
        diaryCount_other: 'Diary {{count}}',
        taskCount_one: 'Task {{count}}',
        taskCount_other: 'Tasks {{count}}',
        scheduledCount_one: '{{count}} task',
        scheduledCount_other: '{{count}} tasks',
        taskCountLoading: 'Tasks …',
        taskCountUnknown: 'Tasks unknown',
        attentionCount_one: '{{count}} item needs attention',
        attentionCount_other: '{{count}} items need attention',
        attentionCountLoading: 'Checking items needing attention…',
        attentionCountUnknown: 'Items needing attention unknown',
        scheduledSectionTitle: 'Scheduled tasks',
        scheduledSectionTitleForDate: 'Scheduled tasks · {{date}}',
        scheduledEmpty: 'No scheduled tasks for this date.',
        scheduledLoading: 'Loading tasks…',
        scheduledUnavailable: 'Tasks are temporarily unavailable.',
        scheduledRetry: 'Retry',
        scheduledConflict: 'This task changed. The latest version is shown; review your edits and save again.',
        scheduledActionError: 'Could not update this task. Try again.',
        scheduledInputInvalid: 'Review the required fields. If this local time repeats or does not exist because of daylight saving time, choose another unambiguous local time.',
        scheduledLocalTimeMissing: 'This local time does not exist on that date because the clock changes. Choose another time.',
        scheduledOffsetRequired: 'This local time occurs twice because the clock changes. Choose another unambiguous time.',
        scheduledOffsetInvalid: 'The saved daylight-saving choice no longer matches this date and time. Choose another time.',
        scheduledRunOutcomeUnknown: 'We are confirming whether this run was created. Checking again reuses the same request and will not create a second run.',
        scheduledTitle: 'Title', scheduledPrompt: 'Prompt', scheduledRule: 'Schedule',
        scheduledStatusLabel: 'Status', scheduledRunAt: 'Run time',
        scheduledArrangePlaceholder: 'Schedule a task', scheduledArrange: 'Continue in Chat',
        scheduledBackToList: 'Back to scheduled tasks', scheduledResultTitle: 'Latest execution',
        scheduledResultUnavailable: 'The latest result is unavailable. Open the run conversation to review it.',
        scheduledResultLoading: 'Loading the latest result…',
        scheduledOnce: 'Once', scheduledDaily: 'Daily', scheduledDate: 'Date',
        scheduledTime: 'Time', scheduledTimeZone: 'Time zone',
        scheduledNext: 'Next run', scheduledSave: 'Save', scheduledCancel: 'Cancel',
        scheduledEdit: 'Edit', scheduledPause: 'Pause', scheduledResume: 'Resume',
        scheduledRun: 'Run now', scheduledDelete: 'Delete', scheduledRestore: 'Undo delete',
        scheduledHistory: 'History', scheduledManual: 'Manual run',
        scheduledPlanned: 'Scheduled run',
        scheduledMore: 'More actions',
        scheduledRecent: 'Latest execution',
        scheduledNeverRun: 'Not run yet',
        scheduledNextPaused: 'The next run will be recalculated after resume.',
        scheduledNextExhausted: 'The one-time schedule is complete. Create a new task in Chat to schedule another time.',
        scheduledNextUnavailable: 'No upcoming run is currently scheduled.',
        scheduledRunBlocked: 'A run is still executing or awaiting verification. Run now is unavailable until it is resolved.',
        scheduledCheckRun: 'Check run request',
        scheduledRequesting: 'Requesting…',
        scheduledSaving: 'Saving…',
        scheduledSkipped: 'This occurrence was skipped. Open history to review its scheduled time.',
        scheduledFailure: 'This run failed. Check the plan before trying again.',
        scheduledUnknown: 'The result is being checked. Open the conversation for details.',
        scheduledOpenThread: 'Open conversation',
        scheduledActionAria: '{{action}}: {{title}}',
        scheduledDeletedTitle: 'Deleted “{{title}}”',
        scheduledDeletedRunning: 'An execution already in progress continues.',
        scheduledEditTitle: 'Edit “{{title}}”',
        scheduledFieldRequired: 'This field is required.',
        scheduledTimeZoneInvalid: 'Enter a valid IANA time zone, such as Asia/Shanghai.',
        scheduledSelectedOffset: 'Current daylight-saving choice: UTC offset {{offset}} minutes. Changing the date, time, or time zone clears it.',
        scheduledLatestEffective: 'Latest saved configuration',
        scheduledConflictFields: 'Your draft differs in: {{fields}}.',
        scheduledConflictNoFields: 'no visible fields',
        scheduledRetryLatest: 'Save using latest version',
        scheduledDiscardDraft: 'Discard draft',
        scheduledDiscardConfirm: 'Discard your unsaved task changes?',
        scheduledHistoryTitle: 'Execution history: {{title}}',
        scheduledClosePanel: 'Close panel',
        scheduledHistoryUnavailable: 'Execution history is temporarily unavailable.',
        scheduledLoadingHistory: 'Loading execution history…',
        scheduledNoHistory: 'No execution history yet.',
        scheduledLoadOlder: 'Load older runs',
        scheduledLoadingOlder: 'Loading older runs…',
        scheduledOlderHistoryUnavailable: 'Older execution history is temporarily unavailable.',
        scheduledAutoRefreshPaused: 'This run is still in progress. Automatic refresh has paused.',
        scheduledRefreshDate: 'Refresh this date',
        scheduledStatus: {
          active: 'Enabled', paused: 'Paused', exhausted: 'Completed schedule',
          deleted: 'Deleted', claimed: 'Preparing', queued: 'Queued', running: 'Running',
          succeeded: 'Completed', failed: 'Failed', state_unknown: 'Checking status', skipped: 'Skipped'
        }
      },
      friends: {
        myFriends: 'My Friends',
        requests: 'Requests',
        addFriend: 'Add Friend',
        noFriends: 'No friends yet. Use an invite code to add your first friend!',
        noRequests: 'No pending friend requests',
        loading: 'Loading...',
        viewTimeline: 'View Timeline',
        remove: 'Remove',
        accept: 'Accept',
        reject: 'Reject',
        generateInvite: 'Generate Invite Code',
        generateHint: 'Share this code with someone to let them send you a friend request. Code expires in 7 days.',
        generate: 'Generate Code',
        generating: 'Generating...',
        copy: 'Copy',
        codeCopied: 'Code copied to clipboard!',
        expiresAt: 'Expires',
        useInvite: 'Use Invite Code',
        useHint: 'Enter a friend\'s invite code to send them a friend request.',
        codePlaceholder: 'Enter 6-character code',
        send: 'Send Request',
        sending: 'Sending...',
        requestSent: 'Friend request sent!',
        confirmRemove: 'Remove this friend?',
        generateError: 'Failed to generate invite code',
        useCodeError: 'Invalid or expired code',
        acceptError: 'Failed to accept request',
        rejectError: 'Failed to reject request',
        removeError: 'Failed to remove friend'
      },
      chat: {
        scheduledTask: {
          createdList: 'Scheduled tasks created in this reply', open: 'Open',
          openAria: 'Open scheduled task: {{title}}', detailTitle: 'Scheduled task',
          close: 'Close scheduled task details', loading: 'Loading task details…',
          unavailable: 'Task details are temporarily unavailable.', details: 'Details',
        },
        deck: {
          none: 'No Deck',
          noneAgent: 'No Agent',
          loading: 'Loading…',
          loadingAgents: 'Loading Agents…',
          loadFailed: 'Failed to load Decks.',
          routeUnavailable: 'This Deck no longer exists, is disabled, or you do not have access.',
          selectAria: 'Select one Deck for this conversation',
          selectTitle: 'Optionally load a Deck and its configured plugin for this conversation.',
          selectAgentAria: 'Select an Agent for this conversation',
          selectAgentTitle: 'Select an Agent; its parent Deck provides plugins and runtime context.',
          agentListAria: 'Agents grouped by Deck',
          searchPlaceholder: 'Type a prefix to filter Decks…',
          searchAgentPlaceholder: 'Filter Decks or Agents…',
          noMatch: 'No Deck matches this prefix',
          noAgentMatch: 'No Agent matches this prefix',
          agentCount_one: '{{count}} agent',
          agentCount_other: '{{count}} agents',
          lockedAria: 'Conversation Deck: {{name}}',
          lockedAgentAria: 'Conversation Agent: {{name}}',
          lockedTitle: 'The Deck is fixed when the conversation starts.',
          metadataTitle: 'Deck metadata',
          metadataDeckName: 'Deck name',
          metadataAgents: 'Agents',
          metadataPlugins: 'Plugin manifest',
          metadataNoDeck: 'No Deck bound to this conversation',
          metadataFrozen: 'Workspace frozen for this conversation',
          metadataCurrentAgent: 'current',
          currentAgent: '{{agent}}, current Agent',
          switchAgent: 'Switch to {{agent}}',
          metadataPacking: 'Plugins will show resolved versions and digests after the first run packs the workspace.',
          metadataNoPlugins: 'This Deck has no plugins configured.',
          metadataCopyDigest: 'Copy digest',
          metadataCopied: 'Copied'
        },
        quickActions: {
          generateImage: {
            label: 'Generate image',
            prompt: 'Generate an image with a consistent style based on the current content, suitable for inserting into the document.',
            description: 'Quickly generate an illustration for the current topic.'
          },
          writeEdit: {
            label: 'Write or edit',
            prompt: 'Help me write, rewrite, or polish the current content, keeping a natural tone consistent with the context.',
            description: 'Continue writing, rewriting, or polishing.'
          },
          findInfo: {
            label: 'Find information',
            prompt: 'Find relevant materials, references, and useful leads around the current topic.',
            description: 'Search for related materials and references.'
          }
        },
        dateGroup: {
          today: 'Today',
          yesterday: 'Yesterday',
          daysAgo_one: '{{count}} day ago',
          daysAgo_other: '{{count}} days ago',
          last7Days: 'Last 7 days',
          last30Days: 'Last 30 days',
          earlier: 'Earlier'
        },
        history: {
          newChat: 'New chat',
          newShort: 'New',
          creating: 'Creating',
          more: 'More',
          title: 'Chat history',
          subtitle: 'Pick a conversation to continue its context.',
          workspace: 'Workspace',
          share: 'Share',
          linkCopied: 'Link copied',
          createFailed: 'Failed to create the conversation. Please try again later.',
          fallbackTitle: 'New conversation',
          empty: 'No conversations yet',
          allShown: 'All conversations shown',
          deleteThread: 'Delete conversation',
          close: 'Close'
        },
        historyTurn: {
          loading: 'Loading conversation…',
          duration: 'Took {{duration}}',
          viewProcess: 'View process',
          expandAria: 'Expand process, {{label}}',
          collapseAria: 'Collapse process, {{label}}',
          expandAriaNoDuration: 'Expand process',
          collapseAriaNoDuration: 'Collapse process',
          loadEarlier: 'Load earlier messages',
          loadingEarlier: 'Loading earlier messages…',
          loadingProcess: 'Loading process…',
          processLoadFailed: 'Process could not be loaded.',
          loadFailed: 'Earlier messages could not be loaded.',
          initialLoadFailed: 'Conversation history could not be loaded.',
          retry: 'Retry',
          empty: 'No messages yet',
          start: 'Start of conversation'
        },
        share: {
          title: 'Share conversation',
          copyLink: 'Copy link',
          comingSoon: 'Coming soon',
          exportImage: 'Export as image',
          exportImageHint: 'Save the whole conversation as a long image',
          exporting: 'Exporting…',
          exportFailed: 'Export failed. Please try again.',
          workspaceImageUnavailable: 'Workspace image unavailable',
          you: 'You',
          assistant: 'Ink & Memory',
          footer: 'Write today. Remember forever.',
          thinking: 'Thinking',
          truncated: '… (truncated)',
          terminal: 'Terminal',
          write: 'Write',
          writing: 'Writing',
          written: 'Written',
          writeFailed: 'Write failed',
          previewTitle: 'Export preview',
          download: 'Download image',
          back: 'Back',
          partsInfo: '{{count}} parts',
          rendering: 'Rendering the rest of the image…',
          merging: 'Merging…',
          preparingPreview: 'Preparing preview…',
          closeToBackground: 'Close (export continues in background)'
        },
        search: {
          button: 'Search',
          placeholder: 'Search chats...',
          searching: 'Searching...',
          noResults: 'No matching conversations',
          ariaLabel: 'Search chat history',
          closeAria: 'Close search'
        },
        tabs: {
          switcherAria: 'Chat workspace switcher',
          history: 'Chat history',
          activeDreams: 'Dreams ({{count}})'
        },
        dream: {
          selectAgent: 'Select an Agent in this Dream Deck first.',
          attachmentsUnsupported: 'Start the Dream with a text goal; attachments are not supported by the current launch contract.',
          launchFailed: 'Dream could not be started.',
          refresh: 'Refresh',
          listFailed: 'Dreams could not be loaded. Try again.',
          empty: 'No Dreams are available to resume.',
          listAria: 'Resumable Dreams',
          open: 'Continue'
        },
        autoRepair: {
          source: 'Workbench auto-repair',
          failed: 'Workbench auto-repair · stopped'
        },
        filters: {
          filterAll: 'Filter: All',
          sortRecent: 'Sort: Recent activity'
        },
        toolConfirmation: {
          userRejectedTool: 'User rejected the tool execution',
          userCancelledAnswer: 'User cancelled the question',
          askUserTitle: 'I&M needs your answer',
          confirmTitle: 'Allow I&M to call the {{tool}} tool',
          rejectOnlyTitle: 'This request requires safe handling',
          rejectOnlyDescription: 'The original request cannot be displayed safely. Reject it so the Dream Agent can continue.',
          rejectAndContinue: 'Reject and continue',
          unknownTool: 'unknown',
          withSummary: ' — {{summary}}',
          pendingAnswer: 'Awaiting answer',
          pendingApproval: 'Awaiting approval',
          pendingConfirm: 'Pending',
          submit: 'Submit',
          cancel: 'Cancel',
          commandPrefix: 'Command: ',
          paramsPrefix: 'Parameters: ',
          reject: 'Reject',
          approve: 'Approve',
          submitting: 'Submitting…',
          processing: 'Processing…',
          answerSubmitted: 'Answer submitted',
          approved: 'Approved',
          cancelled: 'Cancelled',
          rejected: 'Rejected',
          networkConfirmTitle: 'Allow I&M to make a network request via {{tool}}',
          networkHostLabel: 'Host: ',
          networkHostUnknown: 'unknown (network shell command)',
          networkPolicyLabel: 'Network policy: ',
          networkPolicyAllowlist: 'Allowlist (domain not matched)',
          networkPolicyOpen: 'Open network (ask every time)'
        },
        askUser: {
          header: 'Your input is needed',
          selectOption: 'Select an option…',
          yes: 'Yes',
          fallbackQuestion: 'Please answer the question',
          questionNumber: 'Question {{number}}'
        },
        mcpApps: {
          regionLabel: 'Interactive tool result',
          unavailable: 'Interactive view unavailable. The saved result above is unchanged.',
          retry: 'Try interactive view again',
          open: 'Open interactive view',
          close: 'Close interactive view'
        },
        editorWrite: {
          userRejected: 'User rejected the editor write operation',
          loading: 'Loading…',
          processing: 'Processing…',
          accepted: 'Operation accepted',
          rejected: 'Operation rejected',
          reasonLabel: 'Reason',
          rejectReasonLabel: 'Rejection reason (optional)',
          rejectReasonPlaceholder: 'Explain why you are rejecting this to help the Agent adjust…',
          confirmReject: 'Confirm rejection',
          addRejectNote: 'Add a rejection note',
          rejectDirectly: 'Reject without a note',
          writeSegmentTitle: 'Agent suggests editing text content',
          targetSegmentId: 'Target segment ID',
          newContentPreview: 'New content preview',
          acceptChange: 'Accept change',
          reject: 'Reject',
          deleteSegmentTitle: 'Agent suggests deleting a segment (irreversible)',
          segmentToDeleteId: 'Segment ID to delete',
          irreversibleWarning: 'This action is irreversible. A deleted segment cannot be restored through tools.',
          confirmDelete: 'Confirm deletion',
          cancel: 'Cancel',
          insertWidgetTitle: 'Agent suggests inserting a widget',
          widgetType: 'Widget type',
          insertPosition: 'Insert position',
          afterSegment: 'After segment {{id}}',
          documentEnd: 'End of document',
          widgetData: 'Widget data',
          collapse: 'Collapse',
          expandFields: 'Expand ({{count}} fields)',
          acceptInsert: 'Accept insert',
          replyCommentTitle: 'Agent suggests replying to a voice comment',
          targetCommentId: 'Target comment ID',
          replyContent: 'Reply content',
          sendReply: 'Send reply',
          completed: {
            writeSegment: 'Content written',
            deleteSegment: 'Segment deleted',
            insertWidget: 'Widget inserted',
            replyComment: 'Comment replied'
          },
          success: 'Success',
          failure: 'Failed',
          failureTitle: 'The note was not changed',
          failureTargetMissing: 'The note was refreshed, but the target segment no longer exists. Nothing was written; the proposed content is preserved below. Start the edit again from the current note.',
          failureSessionChanged: 'The current note changed before this edit ran. Nothing was written; the proposed content is preserved below. Start the edit again in the current note.',
          failureUnavailable: 'The note could not be saved right now. Nothing was written; the proposed content is preserved below. Please retry later.',
          failureGeneric: 'The edit did not complete. Nothing was written; the proposed content is preserved below. Please retry from the current note.',
          retainedInput: 'Proposed content kept for retry',
          segmentIdPrefix: 'Segment ID: ',
          jumpToNote: 'Jump to note',
          fallbackTitle: 'Agent requests an editor operation: ',
          accept: 'Accept'
        },
        inputDock: {
          toolChoiceAuto: 'Auto',
          toolChoiceAutoTitle: 'Claude decides when to call tools',
          toolChoiceManual: 'Confirm each step',
          toolChoiceManualTitle: 'Every tool call requires manual confirmation',
          workspaceSyncFailed: 'Failed to sync the file to the workspace',
          uploadFailed: 'Upload failed',
          fileTooLarge: '{{name}}: file too large (max {{max}})',
          waitForUpload: 'Please wait for file uploads to finish',
          deleteFileAria: 'Delete file {{name}}',
          uploadHint: 'Upload: paste · drag & drop · click to browse',
          sendShortcut: 'Enter to send · Shift+Enter for a new line',
          inputAria: 'Chat input',
          addAttachmentAria: 'Add attachment',
          addAttachment: '+ Attachment',
          toolAccessAria: 'Tool call permission',
          toolModeAria: 'Tool call mode',
          fullAccess: 'Full access',
          stopping: 'Stopping',
          stopGenerating: 'Stop generating',
          generating: 'Generating',
          subagentsRunning_one: '{{count}} subagent running',
          subagentsRunning_other: '{{count}} subagents running',
          waitingUpload: 'Waiting for uploads…',
          send: 'Send',
          sendAria: 'Send message'
        },
        panel: {
          scrollToBottom: 'Scroll to bottom'
        },
        turnNavigation: {
          label: 'Messages in this conversation',
          itemAria: 'User message {{index}}: {{preview}}',
          summary: 'Interaction summary',
          attachment: 'Attachment sent',
          emptyInput: 'Message content unavailable',
          mobileTitle: 'Messages in this conversation ({{count}})',
          locating: 'Finding message…',
          locateFailed: 'Could not find this message.',
          loadingIndex: 'Loading earlier message navigation…',
          partial: 'Only loaded messages are shown. Retry loading the full list.',
          retryIndex: 'Retry loading message navigation',
          status: {
            answered: 'Reply',
            running: 'Reply in progress',
            failed: 'This turn failed',
            cancelled: 'This turn was stopped',
            no_reply: 'No reply yet',
            state_unknown: 'Reply status needs checking'
          }
        },
        inputQueue: {
          region: 'Queued messages', queued: 'Queued', selected: 'Selected', dispatching: 'Sending',
          consumed: 'Processed', cancelled: 'Cancelled', failed: 'Failed', state_unknown: 'Needs review',
          ownerUnverified: 'Current server cannot verify', guide: 'Adjust direction',
          delete: 'Remove queued message', more: 'More options', edit: 'Edit message',
          save: 'Save', cancelEdit: 'Cancel editing', sideChat: 'Open in side chat',
          closeQueue: 'Close queue',
          sideChatLaunchFailed: 'The side chat was created, but its first response could not start. Open it to review the state.',
          closeSideChat: 'Close side chat',
          editDraftSaved: 'The original queue item was removed. Your edited draft is saved here.',
          retryEdit: 'Retry queuing this draft',
          guideFailed: 'Interrupt failed. This message was not sent to Claude; send it again if needed.',
          textOnly: 'Only text messages can be queued while the Agent is running.',
          accessDenied: 'You cannot access this conversation.', ownerUnavailable: 'The Agent is no longer running here. Reload the conversation.',
          stateChanged: 'The message state changed. Reload the queue and try again.',
          unavailable: 'Messages cannot be queued right now. Your draft is kept.',
          stateUnknown: 'Queue status is uncertain. Your draft is kept; check the queue before sending again.',
          dispatchedStateUnknown: 'This message entered the conversation, but its result needs review. Check the conversation before sending it again.',
          checkStatus: 'Check queue status', checkingStatus: 'Checking…',
          sendFailed: 'The message could not be queued. Your draft is kept.'
        },
        taskSessionNavigation: {
          fromSource: 'Created from another task',
          fromNamedSource: 'Created from “{{title}}”',
          backToSourceAria: 'Open the source conversation',
          listTitle: 'Tasks created by this conversation',
          listCount_one: 'Task created by this conversation · {{count}}',
          listCount_other: 'Tasks created by this conversation · {{count}}',
          created: 'Created',
          failed: 'Start failed',
          openChat: 'Open chat',
          unavailable: 'Task relationships are temporarily unavailable.',
          retry: 'Reload'
        },
        taskActivity: {
          activityTitle: 'Task activity', sectionsAria: 'Tasks and agents', createdTasks: 'Tasks created',
          noTasks: 'No tasks created in this conversation.', loading: 'Loading tasks…',
          unavailable: 'Tasks could not be loaded.', retry: 'Reload', refresh: 'Refresh',
          status: { pending: 'Pending', failed: 'Start failed', running: 'Running', idle: 'Ended', completed: 'Completed', state_unknown: 'Status unavailable' }
        },
        turnError: {
          bindingConflictTitle: 'This conversation cannot continue the Dream yet',
          bindingConflictDescription: 'To avoid writing into the wrong creative task, the Agent did not start. Your message and attachments remain in the conversation. Reload the conversation; if it is still unavailable, start a new conversation from the top bar.',
          autoRepairFailedTitle: 'Workbench auto-repair stopped',
          autoRepairFailedDescription: 'The one automatic repair attempt did not pass the final workspace validation. Reload the conversation to review the retained repair message and latest state.',
          artifactSyncFailedTitle: 'Reply saved; workbench sync incomplete',
          artifactSyncFailedDescription: 'The Agent reply remains in this conversation, but Dream did not finish synchronizing the workbench. Reload the conversation to reconcile its latest persisted state; this will not resend your message.',
          allowanceExhaustedTitle: 'Subscription Token allowance is insufficient',
          allowanceExhaustedDescription: 'Your message was saved, but the model could not complete a reply because this subscription period does not have enough available Tokens. Adjust the subscription allowance or model configuration, then reload the conversation before deciding whether to send again.',
          genericTitle: 'The message was not processed',
          genericDescription: 'Reload the conversation to check its latest state before deciding whether to send again.',
          reload: 'Reload conversation',
          reloading: 'Reloading…'
        },
        planPanel: {
          planning: 'Planning',
          exited: 'Exited planning',
          justNow: 'Just now',
          minutesAgo_one: '{{count}} minute ago',
          minutesAgo_other: '{{count}} minutes ago',
          hoursAgo_one: '{{count}} hour ago',
          hoursAgo_other: '{{count}} hours ago',
          daysAgo_one: '{{count}} day ago',
          daysAgo_other: '{{count}} days ago',
          waitingContent: 'Planning triggered, waiting for plan content…',
          noContent: 'No plan content found.',
          loading: 'Loading…',
          loadFull: 'Content truncated — click to load the full plan',
          noTodos: 'No to-dos yet',
          collapse: 'Collapse',
          expandMore: 'Show {{count}} more',
          buttonAria: 'Plan & to-dos',
          tooltip: 'Plan & to-dos',
          planTitle: 'Plan',
          todosTitle: 'To-dos'
        },
        subagents: {
          title: 'Subagents',
          buttonAria: 'Subagent tasks: {{summary}}',
          runningSummary: '{{running}} running · {{completed}} completed',
          completedSummary: '{{count}} completed',
          taskSummary: '{{count}} tasks',
          activeTitle: 'Active',
          noActive: 'No active subagents',
          completedTitle: 'Completed · {{count}}',
          endedTitle: 'Ended · {{count}}',
          empty: 'This conversation has no subagent tasks yet.',
          loading: 'Restoring subagent tasks…',
          refresh: 'Refresh tasks',
          resizeSidebar: 'Resize subagent sidebar. Use arrow keys to adjust; double-click to reset.',
          retry: 'Retry',
          unavailable: 'Could not refresh subagent tasks.',
          noSummary: 'No task summary',
          launched: 'Launched',
          openTask: 'Open subagent task: {{task}}',
          openTaskAria: 'Open subagent task {{task}}. Status: {{status}}. Duration: {{duration}}.',
          taskFallback: 'Subagent task',
          detailTitle: 'Execution details',
          backToTasks: 'Back to subagent tasks',
          agentType: 'Agent',
          startedAt: 'Started',
          duration: 'Duration',
          spawnDepth: 'Delegation depth',
          unknown: 'Unknown',
          resultTitle: 'Latest result',
          errorTitle: 'Execution error',
          executionTitle: 'Execution activity',
          messageActivity: 'Agent update',
          toolActivity: 'Used {{tool}}',
          toolFallback: 'tool',
          noActivity: 'No execution activity was captured for this task.',
          timeline: {
            messageCount_one: '{{count}} message',
            messageCount_other: '{{count}} messages',
            taskDispatch: 'Assigned task',
            agentUpdate: 'Agent update',
            finalReply: 'Final reply',
            toolUsed: 'Used {{tool}}',
            toolInput: 'Input summary',
            toolOutput: 'Result summary',
            statusUpdate: 'Status update',
            running: 'This task is still running. New records appear after refresh.',
            empty: 'No conversation records are available for this task.',
            legacy: 'This historical task only contains a partial summary and activity log.',
            projectionTruncated: 'This timeline is bounded. Some older or oversized records are not shown.',
            redacted: 'Sensitive fields were redacted by the server.',
            truncated: 'This tool record was shortened for safe display.',
            unknownEvent: 'Unsupported event: {{event}}'
          },
          activityStatus: {
            started: 'Started',
            completed: 'Completed',
            failed: 'Failed'
          },
          status: {
            running: 'Running',
            completed: 'Completed',
            failed: 'Failed',
            cancelled: 'Cancelled'
          }
        },
        mermaid: {
          renderFailed: 'Mermaid · render failed',
          rendering: 'Mermaid · rendering…',
          preview: 'Preview',
          source: 'Source',
          copySource: 'Copy Markdown source',
          enlarge: 'Enlarge diagram',
          previewTitle: 'Mermaid diagram preview',
          exportPng: 'Export PNG'
        },
        mediaPreview: {
          close: 'Close preview',
          zoomOut: 'Zoom out',
          zoomIn: 'Zoom in'
        },
        workspaceFile: {
          checking: 'Checking Workspace…',
          loadingImage: 'Loading Workspace image…',
          imageAlt: 'Workspace image',
          previewAction: 'Preview {{name}} at full size',
          previewBadge: 'View full size',
          previewTitle: 'Full-size preview · {{name}}',
          closePreview: 'Close image preview',
          downloadImage: 'Download image',
          downloadFile: 'Download file',
          closeDocumentPreview: 'Close report preview',
          loading: 'Loading…',
          downloading: 'Downloading…',
          downloadStarted: 'Download started.',
          retry: 'Retry',
          access: 'You do not have access to this Workspace file.',
          disabled: 'Workspace is disabled.',
          invalid: 'Invalid Workspace file reference.',
          missing: 'Workspace file not found or unavailable.',
          unsupported: 'This file type cannot be previewed inline.',
          retryable: 'Workspace file could not be loaded.'
        },
        connector: {
          noInteraction: 'No interactions yet',
          status: {
            notConnected: 'Not connected',
            healthy: 'Healthy',
            degraded: 'Needs attention',
            authenticating: 'Authenticating',
            expired: 'Expired',
            error: 'Error'
          },
          auth: {
            authenticated: 'Authorized',
            authenticating: 'Authorizing',
            expired: 'Authorization expired',
            error: 'Authorization error',
            unauthorized: 'Not authorized'
          },
          sync: {
            syncing: 'Syncing',
            synced: 'Synced',
            waitingAuth: 'Awaiting authorization',
            reauthNeeded: 'Re-authorization needed',
            error: 'Sync error',
            mounted: 'Mounted',
            notSynced: 'Not synced',
            pendingSync: 'Pending sync'
          },
          statAuth: 'Auth',
          statSync: 'Sync',
          statResources: 'Resources',
          resourceCount: '{{count}}',
          lastInteraction: 'Last activity {{time}}',
          manage: 'Manage',
          linkedResources: 'Linked resources',
          noLinkedResources: 'No linked resources yet',
          showingProgress: 'Showing {{shown}} of {{total}} — scroll down to load more',
          showingAll: 'Showing all {{count}} resources',
          emptyTitle: 'No resource connectors yet',
          emptyDescription: 'Connect Notion to use selected resources in conversations',
          selectConnector: 'Choose a connector',
          loadFailed: 'Failed to load connector status'
        },
        shellError: {
          history: 'Chat history',
          dreams: 'Active Dreams'
        },
        skeleton: {
          loading: 'Loading'
        },
        upload: {
          serverFailed: 'Server upload failed',
          noFileKey: 'Server did not return a file key',
          parseFailed: 'Failed to parse the upload result',
          failed: 'Upload failed',
          fileRequired: 'A file is required for upload',
          storageLoading: 'Storage service is still loading, please try again later',
          storageNotConfigured: 'Storage service is not configured'
        }
      }
    }
  },
  zh: {
    translation: {
      nav: {
        writing: '写作',
        timeline: '时间线',
        analysis: '回顾',
        decks: '卡组',
        connector: '连接器',
        dream: 'Dream',
        chat: '对话',
        more: '更多',
        friends: '好友',
        settings: '设置'
      },
      writingSuggestion: {
        goDeeper: '深入一下',
        loading: '正在深入…',
        refresh: '重新生成',
        retry: '重试',
        regionLabel: '写作建议',
        threadTitle: '写作建议',
        failed: '建议生成中断，你的正文未受影响。',
        unavailable: '暂时无法生成建议。',
        errors: {
          threadCreate: '无法开始建议对话，请重试。',
          threadPersist: '无法保存建议对话，请重试。',
          interrupted: '建议生成中断，你的正文未受影响。'
        }
      },
      settings: {
        heading: '心灵议会',
        subheading: '在这里整理那些会对你文字发表评论的声音。',
        tabs: {
          voices: '🎭 声线',
          meta: '📜 元提示',
          states: '💭 心情状态'
        },
        language: {
          title: '界面语言',
          description: '切换界面上的文字语言，日记内容保持原样。',
          placeholder: '选择语言',
          preview: '切换后菜单、按钮与说明会立即更新。',
          options: {
            en: 'English (英语)',
            zh: '中文'
          }
        },
        workspace: {
          aria: {
            categories: '设置分类',
            navigation: '设置分类导航',
            content: '设置内容'
          },
          backToApp: '返回应用',
          personal: '个人',
          search: {
            label: '搜索设置',
            placeholder: '搜索设置…',
            noResults: '没有匹配的设置'
          },
          navigation: {
            general: '常规',
            subscription: '订阅',
            work: '工作台',
            model: 'AI 模型',
            about: '关于'
          },
          general: {
            description: '调整界面语言和工作区显示偏好。'
          },
          languageLabel: '语言',
          theme: {
            label: '外观主题',
            description: '选择工作区的显示外观。',
            options: {
              light: '浅色',
              system: '跟随系统',
              dark: '深色'
            }
          },
          energy: {
            label: '能量条',
            description: '在底部统计栏显示能量进度条。',
            toggleLabel: '切换能量条'
          },
          work: {
            title: '工作台',
            description: '集中管理可在创作工作区使用的 Deck、资源链接与插件。',
            tabsLabel: '工作台管理分类',
            tabs: {
              deck: 'Deck',
              resources: '资源链接',
              plugins: '插件'
            }
          },
          resourceDetail: {
            title: '资源连接',
            description: '管理单个资源连接。'
          },
          model: {
            title: 'AI 模型配置',
            description: '配置创作工作区使用的模型和运行策略。'
          },
          about: {
            title: '关于',
            description: 'Ink & Memory 工作区信息。'
          }
        }
      },
      analysis: {
        title: '回顾',
        subtitle: '读出文字里编织的脉络与启示',
        backButton: '返回',
        backTitle: '回到总览',
        stats: {
          days: '天数',
          entries: '篇章',
          words: '字数'
        },
        pastReflections: '历史回顾',
        report: {
          latest: '最新',
          patternCount: '{{count}} 个模式'
        },
        actions: {
          generate: '生成全新分析',
          generating: '解析中...'
        },
        empty: {
          title: '等待解析的故事',
          description: '开始探索文字里反复出现的主题、情绪与线索'
        },
        papers: {
          echoes: { title: '重复回响', subtitle: '主题回声' },
          traits: { title: '性格折射', subtitle: '个性印象' },
          patterns: { title: '行为轨迹', subtitle: '惯性与习惯' }
        },
        statsLabels: {
          daysCount_one: '{{count}} 天',
          daysCount_other: '{{count}} 天',
          entriesCount_one: '{{count}} 篇章',
          entriesCount_other: '{{count}} 篇章',
          wordsCount: '{{value}} 字'
        },
        reportCounts: {
          echoes_one: '{{count}} 个回声',
          echoes_other: '{{count}} 个回声',
          traits_one: '{{count}} 个性格',
          traits_other: '{{count}} 个性格',
          patterns_one: '{{count}} 个模式',
          patterns_other: '{{count}} 个模式'
        }
      },
      deck: {
          loading: '正在加载 Deck…',
          actions: {
            retry: '重试',
            create: '创建 Deck',
            createMenu: '创建',
            creating: '正在创建 Deck…',
            sync: '与原版同步',
            delete: '删除卡组',
            edit: '编辑',
            inspect: '查看模板',
            fork: '创建副本',
            enable: '启用',
            disable: '停用',
            refresh: '刷新',
            refreshing: '刷新中…',
          clearFilters: '清除筛选',
          more: '{{deck}} 的更多操作',
          relatedConversations: '相关对话',
          enableDeck: '启用 {{deck}}',
            disableDeck: '停用 {{deck}}'
        },
        defaults: {
          newName: '新建 Deck',
          newDescription: '请在这里描述你的 Deck'
        },
        home: {
          sectionLabel: 'Deck',
          title: 'Deck',
          description: '管理在 Chat 和 Dream 中使用的 Deck',
          launchDescription: '打开可用的 Deck；草稿及其他 Deck 请前往设置管理',
          enabledTitle: '已安装',
          enabledEmpty: '当前没有可用 Deck。',
          availableEmpty: '当前页面没有可用 Deck。',
          allTitle: '全部 Deck',
          launchCatalogTitle: 'Deck 目录',
          availableTitle: '正式可用 Deck',
          availableListTitle: '可用 Deck',
          availableListLabel: '用户创建的可用 Deck',
          availableListEmpty: '没有符合条件的用户 Deck。',
          systemListTitle: '系统 Deck',
          systemListLabel: '系统内建 Deck',
          systemListEmpty: '当前没有系统 Deck。',
          launchSearchLabel: '搜索正式可用的 Deck',
          launchListLabel: '正式可用 Deck 列表',
          openDeck: '打开 {{deck}}',
          systemDeckLabel: '系统内建 Deck {{deck}}',
          openSettings: '打开 Deck 设置'
        },
        labels: {
          system: '系统',
          systemBuiltIn: '系统内建',
          contentVersion: '内容 v{{version}}',
          noDescription: '暂无简介',
          voiceCount: '{{count}} 条声线',
          agentCount: '{{count}} 个 Agent',
          anonymous: '匿名',
          enabled: '已启用',
          disabled: '已停用',
          updateUnknown: '未记录',
          agentType: {
            chat: 'Chat Agent',
            dream: 'Dream Agent'
          }
        },
        preview: {
          back: '返回 Deck',
          tryNow: '立即试用',
          launchingDream: '正在启动 Dream…',
          launchDreamFailed: 'Dream 启动失败，Deck 选择未改变，请重试。',
          examples: 'Deck 预览示例',
          defaultDescription: '{{deck}} 已可用于 Chat 与 Dream 工作。',
          agentsTitle: 'Agent {{count}}',
          noAgents: '这个 Deck 暂未配置 Agent。',
          infoTitle: '信息',
          infoDeveloper: '开发者',
          systemDeveloper: 'Ink & Memory',
          userDeveloper: '你',
          infoType: '类别',
          infoVersion: '版本',
          infoRuntime: '运行版本',
          infoUpdated: '更新于',
          editDeck: '编辑 Deck {{deck}}'
        },
        creator: {
          searchLabel: '搜索可管理的 Deck',
          searchPlaceholder: '搜索名称或说明',
          agentTypeFilter: '按 Agent 类型筛选',
          agentTypeTabs: {
            all: '全部',
            chat: 'Chat',
            dream: 'Dream'
          },
          statusFilter: '按启用状态筛选',
          statusAll: '全部状态',
          empty: '还没有可管理的 Deck，可新建一个开始。',
          noResults: '没有符合当前条件的 Deck。',
          listLabel: 'Deck 设置列表'
        },
        pagination: {
          ariaLabel: 'Deck 列表分页',
          previous: '上一页',
          next: '下一页',
          summary: '第 {{page}} / {{pages}} 页'
        },
        related: {
          title: '相关对话',
          description: '仍有 Chat 对话使用这个 Deck 时，系统会保护它不被删除。这里沿用 Chat 历史预览，仅删除你确认不再需要的对话。',
          loading: '正在加载相关对话…',
          loadFailed: '相关对话加载失败。',
          deleteFailed: '对话删除失败。',
          emptyTitle: '没有相关对话',
          emptyDescription: 'Chat 历史已不再阻止删除这个 Deck。',
          listLabel: '相关 Chat 对话',
          confirmDelete: '确定删除“{{title}}”吗？对应的 Chat 历史将被永久删除。',
          deleteConversation: '删除对话 {{title}}',
          delete: '删除',
          deleting: '删除中…',
          loadMore: '加载更多',
          loadingMore: '加载中…',
          deleteHint: '需要先删除全部相关对话，才能删除这个 Deck。',
          unknownHint: '请先重试加载相关对话，未知结果不能视为已清空。',
          readyHint: '相关对话已清空，现在可以重新删除 Deck。',
          deleteDeck: '删除 Deck',
          close: '关闭'
        },
        details: {
          createTitle: '新建 Deck',
          editTitle: '编辑 Deck',
          inspectTitle: 'Deck 详情',
          name: 'Deck 名称',
          description: '说明',
          icon: '图标',
          color: '颜色',
          defaultVisual: '使用默认值',
          enableHint: '请在管理列表中启用或停用此 Deck。',
          nameRequired: '请输入 Deck 名称。',
          saveFailed: 'Deck 保存失败，请重试。',
          cancel: '取消',
          close: '关闭',
          save: '保存',
          saving: '保存中…'
        },
        confirm: {
          delete: '确定删除这个卡组以及所有声线？',
          deleteAgent: '确定删除这个 Agent？',
          sync: '与原模板同步？这会覆盖你在卡组里的修改。'
        },
        messages: {
          loadFailed: 'Deck 加载失败。',
          createFailed: 'Deck 创建失败。',
          createAgentFailed: 'Agent 创建失败。',
          updateFailed: 'Deck 更新失败。',
          updateAgentFailed: 'Agent 更新失败。',
          toggleFailed: 'Deck 状态更新失败。',
          forkFailed: 'Deck 副本创建失败。',
          deleteFailed: 'Deck 删除失败。',
          deleteAgentFailed: 'Agent 删除失败。',
          syncFailed: 'Deck 同步失败。'
        }
      },
      timeline: {
        today: '今天',
        entryCount_one: '{{count}} 条记录',
        entryCount_other: '{{count}} 条记录',
        friendSelector: {
          label: '查看时间线',
          placeholder: '选择好友',
          none: '不查看好友',
          loading: '正在加载好友...',
          error: '无法加载好友列表',
          button: '时间线设置',
          summarySolo: '当前仅显示个人时间线',
          summaryWithFriend: '正在与 {{name}} 的时间线对照',
          searchPlaceholder: '搜索好友',
          noFriends: '你还没有好友。',
          noMatches: '没有符合条件的好友',
          close: '关闭',
          personal: '仅自己',
          more: '更多',
          selfOnlyTitle: '只有你在这里',
          selfOnlyHint: '点右侧的好友圆标，就能把 TA 的时间线拉来并排浏览。',
          friendEmptyTitle: '最近没有内容',
          friendEmptyHint: '这位好友在最近几天都没有留下时间线。'
        },
        friendTimeline: {
          loading: '正在加载好友时间线...',
          empty: '这位好友最近没有记录。',
          error: '无法加载好友的时间线。',
          readOnly: '好友的总结仅供查看，无法互动。',
          readOnlyShort: '好友时间线预览'
        }
      },
      calendar: {
        title: '日历',
        subtitle: '选择任意一天重新回到当时的文字',
        empty: '这里还没有记录，动笔就会留下足迹。',
        untitled: '未命名',
        monthCalendarLabel: '月度日记日历',
        deleteConfirm: '确定删除这篇记录？',
        entriesLabel_one: '{{count}} 篇',
        entriesLabel_other: '{{count}} 篇',
        currentEntryLabel: '当前笔记',
        openButton: '打开',
        deleteButton: '删除',
        close: '关闭',
        prev: '← 上个月',
        next: '下个月 →',
        noEntriesForDate: '这一天暂无记录',
        todayLabel: '今天',
        loadError: '无法打开这篇记录。',
        deleteError: '删除失败',
        diarySectionTitle: '日记',
        diarySectionTitleForDate: '{{date}}的日记',
        diaryCount_one: '日记 {{count}}',
        diaryCount_other: '日记 {{count}}',
        taskCount_one: '任务 {{count}}',
        taskCount_other: '任务 {{count}}',
        scheduledCount_one: '{{count}} 项',
        scheduledCount_other: '{{count}} 项',
        taskCountLoading: '任务 …',
        taskCountUnknown: '任务数未知',
        attentionCount_one: '有 {{count}} 项需处理',
        attentionCount_other: '有 {{count}} 项需处理',
        attentionCountLoading: '正在检查需处理项…',
        attentionCountUnknown: '需处理数未知',
        scheduledSectionTitle: '定时任务',
        scheduledSectionTitleForDate: '{{date}}的定时任务',
        scheduledEmpty: '这一天没有定时任务。',
        scheduledLoading: '正在加载任务…',
        scheduledUnavailable: '任务暂不可用。',
        scheduledRetry: '重试',
        scheduledConflict: '任务已变化。已显示最新版本，请检查修改后重试。',
        scheduledActionError: '任务更新失败，请重试。',
        scheduledInputInvalid: '请检查必填字段。如果当地时间因夏令时重复或不存在，请改用另一个明确的当地时间。',
        scheduledLocalTimeMissing: '该日期的这个当地时间因时钟调整而不存在，请选择其他时间。',
        scheduledOffsetRequired: '该当地时间因时钟调整会出现两次，请选择另一个没有歧义的时间。',
        scheduledOffsetInvalid: '已保存的夏令时选择与当前日期时间不再匹配，请选择其他时间。',
        scheduledRunOutcomeUnknown: '正在确认是否已创建本次执行。再次核查会复用同一请求，不会创建第二次执行。',
        scheduledTitle: '标题', scheduledPrompt: '执行提示词', scheduledRule: '计划',
        scheduledStatusLabel: '状态', scheduledRunAt: '执行时间',
        scheduledArrangePlaceholder: '安排任务', scheduledArrange: '在 Chat 中继续',
        scheduledBackToList: '返回定时任务列表', scheduledResultTitle: '最近一次运行结果',
        scheduledResultUnavailable: '最近一次运行结果暂不可用，可打开本次运行会话查看。',
        scheduledResultLoading: '正在加载最近一次运行结果…',
        scheduledOnce: '单次', scheduledDaily: '每天', scheduledDate: '日期',
        scheduledTime: '时间', scheduledTimeZone: '时区',
        scheduledNext: '下次执行', scheduledSave: '保存', scheduledCancel: '取消',
        scheduledEdit: '编辑', scheduledPause: '暂停', scheduledResume: '恢复',
        scheduledRun: '立即运行', scheduledDelete: '删除', scheduledRestore: '撤销删除',
        scheduledHistory: '历史', scheduledManual: '手动执行',
        scheduledPlanned: '计划执行',
        scheduledMore: '更多操作',
        scheduledRecent: '最近执行',
        scheduledNeverRun: '尚未执行',
        scheduledNextPaused: '恢复后重新计算下一次执行。',
        scheduledNextExhausted: '单次计划已完成；重新排期需在 Chat 新建任务。',
        scheduledNextUnavailable: '当前没有即将执行的计划。',
        scheduledRunBlocked: '已有执行仍在进行或等待核查，结果明确前不能再次立即运行。',
        scheduledCheckRun: '核查运行请求',
        scheduledRequesting: '正在请求…',
        scheduledSaving: '正在保存…',
        scheduledSkipped: '本次计划已跳过，可在历史中查看原计划时间。',
        scheduledFailure: '本次执行失败。请检查计划后再试。',
        scheduledUnknown: '执行结果正在核查。可打开关联会话查看详情。',
        scheduledOpenThread: '打开会话',
        scheduledActionAria: '{{action}}：{{title}}',
        scheduledDeletedTitle: '已删除“{{title}}”',
        scheduledDeletedRunning: '已经开始的执行仍会继续。',
        scheduledEditTitle: '编辑“{{title}}”',
        scheduledFieldRequired: '此字段为必填项。',
        scheduledTimeZoneInvalid: '请输入有效的 IANA 时区，例如 Asia/Shanghai。',
        scheduledSelectedOffset: '当前夏令时选择：UTC 偏移 {{offset}} 分钟。修改日期、时间或时区后将清除。',
        scheduledLatestEffective: '最新已生效配置',
        scheduledConflictFields: '你的草稿与最新配置在这些字段不同：{{fields}}。',
        scheduledConflictNoFields: '没有可见字段',
        scheduledRetryLatest: '基于最新版本保存',
        scheduledDiscardDraft: '放弃草稿',
        scheduledDiscardConfirm: '放弃尚未保存的任务修改？',
        scheduledHistoryTitle: '执行历史：{{title}}',
        scheduledClosePanel: '关闭面板',
        scheduledHistoryUnavailable: '执行历史暂不可用。',
        scheduledLoadingHistory: '正在加载执行历史…',
        scheduledNoHistory: '尚无执行记录。',
        scheduledLoadOlder: '加载更早记录',
        scheduledLoadingOlder: '正在加载更早记录…',
        scheduledOlderHistoryUnavailable: '更早的执行记录暂不可用。',
        scheduledAutoRefreshPaused: '本次执行仍在处理中，自动刷新已暂停。',
        scheduledRefreshDate: '刷新当前日期',
        scheduledStatus: {
          active: '已启用', paused: '已暂停', exhausted: '计划已完成',
          deleted: '已删除', claimed: '正在准备', queued: '已加入队列', running: '执行中',
          succeeded: '已完成', failed: '失败', state_unknown: '状态待核对', skipped: '已跳过'
        }
      },
      friends: {
        myFriends: '我的好友',
        requests: '好友申请',
        addFriend: '添加好友',
        noFriends: '还没有好友。使用邀请码添加你的第一个好友吧！',
        noRequests: '暂无待处理的好友申请',
        loading: '加载中...',
        viewTimeline: '查看时间线',
        remove: '移除',
        accept: '接受',
        reject: '拒绝',
        generateInvite: '生成邀请码',
        generateHint: '将此邀请码分享给朋友，让对方向你发送好友申请。邀请码 7 天后过期。',
        generate: '生成邀请码',
        generating: '生成中...',
        copy: '复制',
        codeCopied: '邀请码已复制到剪贴板！',
        expiresAt: '过期时间',
        useInvite: '使用邀请码',
        useHint: '输入朋友的邀请码，向对方发送好友申请。',
        codePlaceholder: '输入 6 位邀请码',
        send: '发送申请',
        sending: '发送中...',
        requestSent: '好友申请已发送！',
        confirmRemove: '确定要移除这位好友吗？',
        generateError: '生成邀请码失败',
        useCodeError: '邀请码无效或已过期',
        acceptError: '接受申请失败',
        rejectError: '拒绝申请失败',
        removeError: '移除好友失败'
      },
      chat: {
        scheduledTask: {
          createdList: '本次回复创建的定时任务', open: '打开',
          openAria: '打开定时任务：{{title}}', detailTitle: '定时任务',
          close: '关闭定时任务详情', loading: '正在加载任务详情…',
          unavailable: '任务详情暂不可用。', details: '详情',
        },
        deck: {
          none: '不使用 Deck',
          noneAgent: '不使用 Agent',
          loading: '加载中…',
          loadingAgents: '正在读取 Agent…',
          loadFailed: 'Deck 加载失败。',
          routeUnavailable: '该 Deck 不存在、已停用，或你没有访问权限。',
          selectAria: '为本次对话单选一个 Deck',
          selectTitle: '可选加载一个 Deck 及其已配置插件。',
          selectAgentAria: '为本次对话选择一个 Agent',
          selectAgentTitle: '选择 Agent；其所属 Deck 提供插件与运行上下文。',
          agentListAria: '按 Deck 分组的 Agent',
          searchPlaceholder: '输入前缀筛选 Deck…',
          searchAgentPlaceholder: '筛选 Deck 或 Agent…',
          noMatch: '没有匹配该前缀的 Deck',
          noAgentMatch: '没有匹配该前缀的 Agent',
          agentCount: '{{count}} 个 Agent',
          lockedAria: '当前对话 Deck：{{name}}',
          lockedAgentAria: '当前对话 Agent：{{name}}',
          lockedTitle: '对话开始后 Deck 将固定，确保运行来源可追溯。',
          metadataTitle: 'Deck 元信息',
          metadataDeckName: 'Deck 名称',
          metadataAgents: 'Agent',
          metadataPlugins: '插件清单',
          metadataNoDeck: '本次对话未绑定 Deck',
          metadataFrozen: '本次对话工作区已锁定',
          metadataCurrentAgent: '当前',
          currentAgent: '{{agent}}，当前 Agent',
          switchAgent: '切换到 {{agent}}',
          metadataPacking: '插件将在首次运行打包工作区后显示版本与摘要。',
          metadataNoPlugins: '此 Deck 未配置插件。',
          metadataCopyDigest: '复制 digest',
          metadataCopied: '已复制'
        },
        quickActions: {
          generateImage: {
            label: '生成图片',
            prompt: '请根据当前内容生成一张风格统一、适合插入文档的图片。',
            description: '根据当前主题快速生成配图。'
          },
          writeEdit: {
            label: '撰写或编辑',
            prompt: '请帮我撰写、改写或润色当前内容，保持自然语气和上下文一致。',
            description: '继续写作、改写或润色。'
          },
          findInfo: {
            label: '查找资料',
            prompt: '请围绕当前主题查找相关资料、参考信息和可用线索。',
            description: '检索相关资料和参考。'
          }
        },
        dateGroup: {
          today: '今天',
          yesterday: '昨天',
          daysAgo_one: '{{count}} 天前',
          daysAgo_other: '{{count}} 天前',
          last7Days: '前 7 天',
          last30Days: '前 30 天',
          earlier: '更早'
        },
        history: {
          newChat: '新建对话',
          newShort: '新建',
          creating: '创建中',
          more: '更多',
          title: '历史对话',
          subtitle: '选择一条对话继续上下文。',
          workspace: '工作空间',
          share: '分享',
          linkCopied: '已复制链接',
          createFailed: '创建对话失败，请稍后再试。',
          fallbackTitle: '新对话',
          empty: '暂无会话',
          allShown: '已显示全部会话',
          deleteThread: '删除对话',
          close: '关闭'
        },
        historyTurn: {
          loading: '正在加载对话…',
          duration: '用时 {{duration}}',
          viewProcess: '查看过程',
          expandAria: '展开执行过程，{{label}}',
          collapseAria: '收起执行过程，{{label}}',
          expandAriaNoDuration: '展开执行过程',
          collapseAriaNoDuration: '收起执行过程',
          loadEarlier: '加载更早消息',
          loadingEarlier: '正在加载更早消息…',
          loadingProcess: '正在加载过程…',
          processLoadFailed: '过程加载失败。',
          loadFailed: '更早消息加载失败。',
          initialLoadFailed: '历史消息加载失败。',
          retry: '重试',
          empty: '暂无消息',
          start: '已到对话开头'
        },
        share: {
          title: '分享对话',
          copyLink: '复制链接',
          comingSoon: '即将上线',
          exportImage: '导出图片',
          exportImageHint: '将整段对话保存为渲染后的长图',
          exporting: '导出中…',
          exportFailed: '导出失败，请重试。',
          workspaceImageUnavailable: '工作空间图片不可用',
          you: '我',
          assistant: 'Ink & Memory',
          footer: 'Write today. Remember forever.',
          thinking: '思考过程',
          truncated: '…（已截断）',
          terminal: '终端',
          write: '写入文件',
          writing: '写入中',
          written: '已写入',
          writeFailed: '写入失败',
          previewTitle: '导出预览',
          download: '下载图片',
          back: '返回',
          partsInfo: '共 {{count}} 张分图',
          rendering: '正在生成剩余部分…',
          merging: '合并中…',
          preparingPreview: '正在生成预览…',
          closeToBackground: '关闭（导出将在后台继续）'
        },
        search: {
          button: '搜索',
          placeholder: '搜索聊天...',
          searching: '搜索中...',
          noResults: '未找到匹配会话',
          ariaLabel: '搜索历史对话',
          closeAria: '关闭搜索'
        },
        tabs: {
          switcherAria: 'Chat 工作区切换',
          history: '聊天历史',
          activeDreams: 'Dream（{{count}}）'
        },
        dream: {
          selectAgent: '请先在 Dream Deck 中选择一个 Agent。',
          attachmentsUnsupported: '请先用文字目标发起 Dream；当前启动合同不接受附件。',
          launchFailed: 'Dream 发起失败。',
          refresh: '刷新',
          listFailed: 'Dream 列表加载失败，请重试。',
          empty: '当前没有可恢复的 Dream。',
          listAria: '可恢复的 Dream',
          open: '继续查看'
        },
        autoRepair: {
          source: '工作台自动修正',
          failed: '工作台自动修正 · 已停止'
        },
        filters: {
          filterAll: '筛选：全部',
          sortRecent: '排序：最近交互'
        },
        toolConfirmation: {
          userRejectedTool: '用户拒绝执行工具',
          userCancelledAnswer: '用户取消了问题回答',
          askUserTitle: 'I&M 需要你的回答',
          confirmTitle: '是否允许 I&M 调用 {{tool}} 工具',
          rejectOnlyTitle: '此请求需要安全处理',
          rejectOnlyDescription: '原始请求无法安全展示。请拒绝本次操作，让 Dream Agent 回到可继续处理的状态。',
          rejectAndContinue: '拒绝并继续',
          unknownTool: '未知',
          withSummary: '，{{summary}}',
          pendingAnswer: '待回答',
          pendingApproval: '待授权',
          pendingConfirm: '待确认',
          submit: '提交',
          cancel: '取消',
          commandPrefix: '命令：',
          paramsPrefix: '参数：',
          reject: '拒绝',
          approve: '同意',
          submitting: '提交中…',
          processing: '处理中…',
          answerSubmitted: '答案已提交',
          approved: '已同意',
          cancelled: '已取消',
          rejected: '已拒绝',
          networkConfirmTitle: '是否允许 I&M 通过 {{tool}} 发起网络请求',
          networkHostLabel: '目标主机：',
          networkHostUnknown: '未知（网络类命令）',
          networkPolicyLabel: '网络策略：',
          networkPolicyAllowlist: '白名单（域名未命中）',
          networkPolicyOpen: '开放网络（每次询问）'
        },
        askUser: {
          header: '需要你的输入',
          selectOption: '请选择…',
          yes: '是',
          fallbackQuestion: '请回答问题',
          questionNumber: '问题 {{number}}'
        },
        mcpApps: {
          regionLabel: '交互式工具结果',
          unavailable: '交互视图暂时不可用，上方已保存的结果不会改变。',
          retry: '重试交互视图',
          open: '打开交互视图',
          close: '关闭交互视图'
        },
        editorWrite: {
          userRejected: '用户拒绝了编辑器写操作',
          loading: '加载中…',
          processing: '处理中…',
          accepted: '操作已接受',
          rejected: '操作已拒绝',
          reasonLabel: '操作理由',
          rejectReasonLabel: '拒绝理由（可选）',
          rejectReasonPlaceholder: '说明拒绝原因，帮助 Agent 调整方案…',
          confirmReject: '确认拒绝',
          addRejectNote: '添加拒绝说明',
          rejectDirectly: '不添加说明，直接拒绝',
          writeSegmentTitle: 'Agent 建议修改文字内容',
          targetSegmentId: '目标片段 ID',
          newContentPreview: '新内容预览',
          acceptChange: '接受修改',
          reject: '拒绝',
          deleteSegmentTitle: 'Agent 建议删除片段（不可逆操作）',
          segmentToDeleteId: '将删除片段 ID',
          irreversibleWarning: '此操作不可逆，片段删除后无法通过工具恢复。',
          confirmDelete: '确认删除',
          cancel: '取消',
          insertWidgetTitle: 'Agent 建议插入组件',
          widgetType: '组件类型',
          insertPosition: '插入位置',
          afterSegment: '片段 {{id}} 之后',
          documentEnd: '文档末尾',
          widgetData: '组件数据',
          collapse: '收起',
          expandFields: '展开（{{count}} 个字段）',
          acceptInsert: '接受插入',
          replyCommentTitle: 'Agent 建议回复语音评论',
          targetCommentId: '目标评论 ID',
          replyContent: '回复内容',
          sendReply: '发送回复',
          completed: {
            writeSegment: '已写入内容',
            deleteSegment: '已删除片段',
            insertWidget: '已插入组件',
            replyComment: '已回复评论'
          },
          success: '成功',
          failure: '失败',
          failureTitle: '笔记未发生更改',
          failureTargetMissing: '笔记已刷新，但目标片段已不存在。本次未写入，拟写内容已保留在下方；请基于当前笔记重新发起操作。',
          failureSessionChanged: '执行前当前笔记已切换。本次未写入，拟写内容已保留在下方；请在当前笔记中重新发起操作。',
          failureUnavailable: '目前暂时无法保存笔记。本次未写入，拟写内容已保留在下方；请稍后重试。',
          failureGeneric: '本次编辑未完成，笔记没有发生更改；拟写内容已保留在下方，请基于当前笔记重试。',
          retainedInput: '已保留的拟写内容',
          segmentIdPrefix: '片段 ID：',
          jumpToNote: '跳转到笔记',
          fallbackTitle: 'Agent 请求执行编辑器操作：',
          accept: '接受'
        },
        inputDock: {
          toolChoiceAuto: '自动',
          toolChoiceAutoTitle: 'Claude 自主决定是否调用工具',
          toolChoiceManual: '逐步确认',
          toolChoiceManualTitle: '每次工具调用都需要手动确认',
          workspaceSyncFailed: '工作空间文件同步失败',
          uploadFailed: '上传失败',
          fileTooLarge: '{{name}}: 文件过大 (最大 {{max}})',
          waitForUpload: '请等待文件上传完成',
          deleteFileAria: '删除文件 {{name}}',
          uploadHint: '上传方式：粘贴 · 拖拽 · 点击选择',
          sendShortcut: 'Enter 发送 · Shift+Enter 换行',
          inputAria: '聊天输入',
          addAttachmentAria: '添加附件',
          addAttachment: '+ 附件',
          toolAccessAria: '工具调用权限',
          toolModeAria: '工具调用模式',
          fullAccess: '完全访问',
          stopping: '正在停止',
          stopGenerating: '停止生成',
          generating: '生成中',
          subagentsRunning: '{{count}} 个子智能体运行中',
          waitingUpload: '等待上传完成…',
          send: '发送',
          sendAria: '发送消息'
        },
        panel: {
          scrollToBottom: '滚动到底部'
        },
        turnNavigation: {
          label: '本对话的消息导航',
          itemAria: '第 {{index}} 条用户消息：{{preview}}',
          summary: '交互摘要',
          attachment: '已发送附件',
          emptyInput: '消息内容不可用',
          mobileTitle: '本对话消息（{{count}}）',
          locating: '正在定位消息…',
          locateFailed: '暂时无法定位这条消息。',
          loadingIndex: '正在加载更早消息的导航…',
          partial: '目前只显示已加载的消息，点击重试完整列表。',
          retryIndex: '重试加载消息导航',
          status: {
            answered: '已有回复',
            running: '正在回复',
            failed: '本轮失败',
            cancelled: '本轮已停止',
            no_reply: '暂无回复',
            state_unknown: '回复状态待核对'
          }
        },
        inputQueue: {
          region: '待处理消息', queued: '排队中', selected: '已选中', dispatching: '正在发送',
          consumed: '已消费', cancelled: '已取消', failed: '发送失败', state_unknown: '状态待核对',
          ownerUnverified: '当前节点无法核实', guide: '调整方向',
          delete: '删除排队消息', more: '更多操作', edit: '编辑消息',
          save: '保存', cancelEdit: '取消编辑', sideChat: '在侧边聊天中打开',
          closeQueue: '关闭排队',
          sideChatLaunchFailed: '侧边聊天已创建，但首轮未能启动。请在侧边栏查看状态。',
          closeSideChat: '关闭侧边聊天',
          editDraftSaved: '原排队消息已移除，修改后的草稿保留在此。',
          retryEdit: '重试加入队列',
          guideFailed: '中断请求失败；这条消息未提交给 Claude，需要时请重新发送。',
          textOnly: 'Agent 运行期间的排队消息目前只支持文字。',
          accessDenied: '无权访问当前对话。', ownerUnavailable: 'Agent 已不在当前节点运行，请重新加载对话。',
          stateChanged: '消息状态已变化，请刷新队列后重试。',
          unavailable: '暂时无法排队，草稿已保留。',
          stateUnknown: '排队结果待核对，草稿已保留；再次发送前请先检查队列。',
          dispatchedStateUnknown: '消息已进入对话，但处理结果待核对；再次发送前请先检查对话。',
          checkStatus: '检查队列状态', checkingStatus: '检查中…',
          sendFailed: '消息未能排队，草稿已保留。'
        },
        taskSessionNavigation: {
          fromSource: '由另一项任务创建',
          fromNamedSource: '由“{{title}}”创建',
          backToSourceAria: '打开来源对话',
          listTitle: '此对话创建的任务',
          listCount: '此对话创建的任务 · {{count}}',
          created: '已创建',
          failed: '启动失败',
          openChat: '打开聊天',
          unavailable: '任务关系暂时无法读取。',
          retry: '重新加载'
        },
        taskActivity: {
          activityTitle: '任务与进度', sectionsAria: '任务与子智能体', createdTasks: '已创建的任务',
          noTasks: '此对话尚未创建任务。', loading: '正在加载任务…',
          unavailable: '暂时无法读取任务。', retry: '重新加载', refresh: '刷新',
          status: { pending: '待启动', failed: '启动失败', running: '运行中', idle: '已结束', completed: '已完成', state_unknown: '状态待核对' }
        },
        turnError: {
          bindingConflictTitle: '当前对话暂时无法继续创作',
          bindingConflictDescription: '为避免把内容写入错误的创作任务，本次 Agent 未开始处理。消息和附件已保留在对话记录中。请重新加载对话状态；如果仍无法继续，可从页面顶部新建对话。',
          autoRepairFailedTitle: '工作台自动修正已停止',
          autoRepairFailedDescription: '唯一一次自动修正未通过最终工作区校验。请重新加载对话，查看已保留的修正消息和最新状态。',
          artifactSyncFailedTitle: '回复已保存，工作台同步未完成',
          artifactSyncFailedDescription: 'Agent 回复已保留在当前对话中，但 Dream 未完成工作台同步。请重新加载对话以核对最新持久化状态；这不会重新发送消息。',
          allowanceExhaustedTitle: '当前订阅周期 Token 不足',
          allowanceExhaustedDescription: '你的消息已经保存，但当前订阅周期没有足够的可用 Token，模型未能完成回复。请调整订阅额度或模型配置，然后重新加载对话，再决定是否重新发送。',
          genericTitle: '消息处理未完成',
          genericDescription: '请重新加载对话以确认最新状态，再决定是否重新发送。',
          reload: '重新加载对话',
          reloading: '正在重新加载…'
        },
        planPanel: {
          planning: '规划中',
          exited: '已退出规划',
          justNow: '刚刚',
          minutesAgo_one: '{{count}} 分钟前',
          minutesAgo_other: '{{count}} 分钟前',
          hoursAgo_one: '{{count}} 小时前',
          hoursAgo_other: '{{count}} 小时前',
          daysAgo_one: '{{count}} 天前',
          daysAgo_other: '{{count}} 天前',
          waitingContent: '规划已触发，等待计划内容…',
          noContent: '未找到计划内容。',
          loading: '加载中…',
          loadFull: '内容已截断，点击加载完整',
          noTodos: '暂无待办',
          collapse: '收起',
          expandMore: '展开 {{count}} 个',
          buttonAria: '计划与待办',
          tooltip: '计划与待办',
          planTitle: '计划',
          todosTitle: '待办'
        },
        subagents: {
          title: '子智能体',
          buttonAria: '子智能体任务：{{summary}}',
          runningSummary: '{{running}} 运行中 · {{completed}} 完成',
          completedSummary: '{{count}} 完成',
          taskSummary: '{{count}} 个任务',
          activeTitle: '已开启',
          noActive: '没有已开启的子智能体',
          completedTitle: '完成 · {{count}}',
          endedTitle: '已结束 · {{count}}',
          empty: '此会话还没有子智能体任务。',
          loading: '正在恢复子智能体任务…',
          refresh: '刷新任务',
          resizeSidebar: '调整子智能体侧栏宽度。可使用方向键调整，双击恢复默认宽度。',
          retry: '重试',
          unavailable: '无法刷新子智能体任务。',
          noSummary: '暂无任务摘要',
          launched: '已发起',
          openTask: '打开子智能体任务：{{task}}',
          openTaskAria: '打开子智能体任务 {{task}}。状态：{{status}}。耗时：{{duration}}。',
          taskFallback: '子智能体任务',
          detailTitle: '执行详情',
          backToTasks: '返回子智能体任务列表',
          agentType: '智能体',
          startedAt: '开始时间',
          duration: '执行耗时',
          spawnDepth: '委派深度',
          unknown: '未知',
          resultTitle: '最新结果',
          errorTitle: '执行错误',
          executionTitle: '执行记录',
          messageActivity: '智能体更新',
          toolActivity: '调用 {{tool}}',
          toolFallback: '工具',
          noActivity: '此任务没有可展示的执行记录。',
          timeline: {
            messageCount: '{{count}} 条消息',
            taskDispatch: '派发任务',
            agentUpdate: '智能体更新',
            finalReply: '最终回复',
            toolUsed: '调用 {{tool}}',
            toolInput: '输入摘要',
            toolOutput: '结果摘要',
            statusUpdate: '状态更新',
            running: '任务仍在执行，刷新后可查看新记录。',
            empty: '此任务没有可展示的对话记录。',
            legacy: '该历史任务仅保留部分摘要与活动记录。',
            projectionTruncated: '时间线采用有界投影，部分较早或过长记录未显示。',
            redacted: '服务端已隐藏敏感字段。',
            truncated: '该工具记录已缩短以便安全展示。',
            unknownEvent: '暂不支持的事件：{{event}}'
          },
          activityStatus: {
            started: '已开始',
            completed: '已完成',
            failed: '失败'
          },
          status: {
            running: '运行中',
            completed: '已完成',
            failed: '失败',
            cancelled: '已取消'
          }
        },
        mermaid: {
          renderFailed: 'Mermaid · 渲染失败',
          rendering: 'Mermaid · 渲染中…',
          preview: '预览',
          source: '源码',
          copySource: '复制 Markdown 源码',
          enlarge: '放大图表',
          previewTitle: 'Mermaid 图表预览',
          exportPng: '导出 PNG'
        },
        mediaPreview: {
          close: '关闭预览',
          zoomOut: '缩小',
          zoomIn: '放大'
        },
        workspaceFile: {
          checking: '正在检查工作空间…',
          loadingImage: '正在加载工作空间图片…',
          imageAlt: '工作空间图片',
          previewAction: '查看 {{name}} 大图',
          previewBadge: '查看大图',
          previewTitle: '大图预览 · {{name}}',
          closePreview: '关闭图片预览',
          downloadImage: '下载图片',
          downloadFile: '下载文件',
          closeDocumentPreview: '关闭报告预览',
          loading: '正在加载…',
          downloading: '正在下载…',
          downloadStarted: '已开始下载。',
          retry: '重试',
          access: '你无权访问此工作空间文件。',
          disabled: '工作空间已关闭。',
          invalid: '工作空间文件引用无效。',
          missing: '工作空间文件不存在或不可用。',
          unsupported: '此文件类型不支持内联预览。',
          retryable: '工作空间文件加载失败。'
        },
        connector: {
          noInteraction: '暂无交互',
          status: {
            notConnected: '未连接',
            healthy: '健康',
            degraded: '部分可用',
            authenticating: '认证中',
            expired: '已过期',
            error: '异常'
          },
          auth: {
            authenticated: '已授权',
            authenticating: '授权中',
            expired: '授权过期',
            error: '授权异常',
            unauthorized: '未授权'
          },
          sync: {
            syncing: '同步中',
            synced: '已同步',
            waitingAuth: '等待授权',
            reauthNeeded: '待重新授权',
            error: '同步异常',
            mounted: '已挂载',
            notSynced: '未同步',
            pendingSync: '待同步'
          },
          statAuth: '授权',
          statSync: '同步',
          statResources: '资源',
          resourceCount: '{{count}} 个',
          lastInteraction: '最近交互 {{time}}',
          manage: '管理',
          linkedResources: '已链接资源',
          noLinkedResources: '暂无已链接资源',
          showingProgress: '已显示 {{shown}} / {{total}}，继续向下滚动加载更多',
          showingAll: '已显示全部 {{count}} 个资源',
          emptyTitle: '暂无资源连接器',
          emptyDescription: '连接 Notion 后可在对话中使用已选择的资源',
          selectConnector: '选择连接器',
          loadFailed: '连接器状态读取失败'
        },
        shellError: {
          history: '历史对话',
          dreams: '进行中的 Dream'
        },
        skeleton: {
          loading: '加载中'
        },
        upload: {
          serverFailed: '服务器上传失败',
          noFileKey: '服务器未返回文件 key',
          parseFailed: '解析上传结果失败',
          failed: '上传失败',
          fileRequired: '上传需要一个文件',
          storageLoading: '存储服务正在加载，请稍后再试',
          storageNotConfigured: '存储服务未配置'
        }
      }
    }
  }
};

const fallback = 'en';

function getInitialLanguage(): string {
  if (typeof window === 'undefined') {
    return fallback;
  }
  return localStorage.getItem(LANGUAGE_STORAGE_KEY) || fallback;
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: fallback,
    interpolation: {
      escapeValue: false
    }
  });

if (typeof window !== 'undefined') {
  i18n.on('languageChanged', (lng) => {
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
    } catch (error) {
      console.warn('Failed to persist language preference:', error);
    }
  });
}

export { LANGUAGE_STORAGE_KEY };
export function getDateLocale(language?: string | null): string {
  if (!language) return 'en-US';
  return language.startsWith('zh') ? 'zh-CN' : 'en-US';
}

export default i18n;
