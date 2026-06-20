import Observation
import StarforgeCore
import StarforgeEngine
import StarforgePersistence
import SwiftUI

@main
struct StarforgeLabApp: App {
    @State private var store = RenderQueueStore()

    var body: some Scene {
        WindowGroup {
            ContentView(store: store)
                .frame(minWidth: 980, minHeight: 680)
        }
        .commands {
            CommandGroup(after: .newItem) {
                Button("Render") {
                    store.render()
                }
                .keyboardShortcut("r", modifiers: [.command])
                .disabled(store.isRendering)
            }
        }

        Settings {
            SettingsView()
        }
    }
}

@MainActor
@Observable
final class RenderQueueStore {
    var request = RenderRequest()
    var isRendering = false
    var logLines: [String] = []
    var latestRecord: RenderRecord?
    var errorMessage: String?

    private let service = RenderService()

    func render() {
        guard !isRendering else { return }
        isRendering = true
        errorMessage = nil
        logLines = []

        Task {
            do {
                let root = try OutputLayout.defaultLibraryRoot()
                let directory = OutputLayout.freshRenderDirectory(in: root)
                for try await event in await service.run(request, into: directory) {
                    apply(event)
                }
            } catch {
                errorMessage = error.localizedDescription
            }
            isRendering = false
        }
    }

    private func apply(_ event: RenderEvent) {
        switch event {
        case .started(let pid):
            logLines.append("started python pid \(pid)")
        case .log(let line):
            logLines.append(line)
        case .manifestReady(let manifest):
            logLines.append("manifest ready: seed \(manifest.selectedSeed)")
        case .finished(let record):
            latestRecord = record
            logLines.append("finished \(record.outputDirectory)")
        case .failed(let error):
            errorMessage = error.localizedDescription
            logLines.append(error.localizedDescription)
        }
    }
}

struct ContentView: View {
    @Bindable var store: RenderQueueStore
    @State private var selection: Section = .create

    var body: some View {
        NavigationSplitView {
            List(Section.allCases, selection: $selection) { section in
                Label(section.title, systemImage: section.symbol)
            }
            .navigationTitle("Starforge")
        } detail: {
            switch selection {
            case .create:
                CreateView(store: store)
            case .history:
                HistoryPlaceholder(record: store.latestRecord)
            }
        }
    }
}

enum Section: String, CaseIterable, Identifiable {
    case create
    case history

    var id: String { rawValue }

    var title: String {
        switch self {
        case .create: "Create"
        case .history: "History"
        }
    }

    var symbol: String {
        switch self {
        case .create: "sparkles"
        case .history: "clock"
        }
    }
}

struct CreateView: View {
    @Bindable var store: RenderQueueStore

    var body: some View {
        HSplitView {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    GroupBox("render") {
                        VStack(alignment: .leading, spacing: 12) {
                    TextField("Seed", value: $store.request.seed, format: .number)
                    Picker("Preset", selection: $store.request.preset) {
                        ForEach(Preset.allNames, id: \.self) { Text($0).tag($0) }
                    }
                    Picker("Subject", selection: $store.request.subject) {
                        ForEach(Subject.allNames, id: \.self) { Text($0).tag($0) }
                    }
                    Picker("Curator", selection: $store.request.curator) {
                        ForEach(Curator.allNames, id: \.self) { Text($0).tag($0) }
                    }
                    LabeledContent("Width") {
                        Stepper(value: $store.request.width, in: 64...5000, step: 64) {
                            Text("\(store.request.width)")
                        }
                    }
                    LabeledContent("Height") {
                        Stepper(value: $store.request.height, in: 64...5000, step: 64) {
                            Text("\(store.request.height)")
                        }
                    }
                    LabeledContent("Frames") {
                        Stepper(value: $store.request.frames, in: 2...180) {
                            Text("\(store.request.frames)")
                        }
                    }
                    LabeledContent("Supersample") {
                        Stepper(value: $store.request.supersample, in: 1...3) {
                            Text("\(store.request.supersample)")
                        }
                    }
                        }
                }

                    GroupBox("exploration") {
                        VStack(alignment: .leading, spacing: 12) {
                    Stepper("Seed gallery \(store.request.seedGallery)", value: $store.request.seedGallery, in: 0...64)
                    Stepper("Batch \(store.request.batch)", value: $store.request.batch, in: 0...128)
                    Stepper("Top K \(store.request.topK)", value: $store.request.topK, in: 0...32)
                    Toggle("Cross subject", isOn: $store.request.crossSubject)
                    Toggle("Studio", isOn: $store.request.studio)
                    Toggle("Video", isOn: $store.request.video)
                    Toggle("Scale preview", isOn: $store.request.scalePreview)
                        }
                }

                if let validation = validationMessage {
                    Text(validation)
                        .foregroundStyle(.red)
                }

                Button(store.isRendering ? "Rendering..." : "Render") {
                    store.render()
                }
                .keyboardShortcut(.return, modifiers: [.command])
                .disabled(store.isRendering || validationMessage != nil)
                }
                .padding(16)
            }
            .frame(minWidth: 320, idealWidth: 360)

            PreviewPane(store: store)
                .frame(minWidth: 560)
        }
        .navigationTitle("Create")
    }

    private var validationMessage: String? {
        do {
            _ = try store.request.validated()
            return nil
        } catch {
            return error.localizedDescription
        }
    }
}

struct PreviewPane: View {
    @Bindable var store: RenderQueueStore

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let record = store.latestRecord {
                Text("seed \(record.manifest.selectedSeed) · \(record.manifest.selectedSubject) · \(record.manifest.selectedPreset)")
                    .font(.headline)
                AsyncImage(url: URL(fileURLWithPath: record.outputDirectory).appendingPathComponent("starforge_poster.png")) { image in
                    image
                        .resizable()
                        .scaledToFit()
                } placeholder: {
                    ProgressView()
                }
            } else if store.isRendering {
                ProgressView("rendering with starforge.cli")
                    .controlSize(.large)
            } else {
                ContentUnavailableView("No render yet", systemImage: "sparkles", description: Text("Choose parameters and run the Python engine."))
            }

            if let error = store.errorMessage {
                Text(error)
                    .foregroundStyle(.red)
                    .textSelection(.enabled)
            }

            ScrollView {
                Text(store.logLines.joined(separator: "\n"))
                    .font(.system(.caption, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .frame(height: 150)
        }
        .padding(20)
    }
}

struct HistoryPlaceholder: View {
    let record: RenderRecord?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("History")
                .font(.title)
            if let record {
                Text(record.outputDirectory)
                    .textSelection(.enabled)
            } else {
                Text("Finished renders will appear here once persistence is wired into the queue.")
                    .foregroundStyle(.secondary)
            }
        }
        .padding(20)
    }
}

struct SettingsView: View {
    var body: some View {
        Form {
            Text("Starforge Lab runs the Python renderer offline as a subprocess.")
                .foregroundStyle(.secondary)
        }
        .padding(20)
        .frame(width: 420)
    }
}
