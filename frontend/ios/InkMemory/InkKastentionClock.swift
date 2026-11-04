// [Input] Shared v4.2 vector/keyframe asset, semantic colors, display mode and visible foreground time.
// [Output] One integrated face/dial with native path morphs and discrete hand jumps.
// [Pos] Narrow RN graphics adapter; Core Animation performs interpolation, with one whole-second timer.
import UIKit
import QuartzCore
import React

private enum ClockVector {
    static func path(_ raw: Any?) -> CGPath {
        let path = CGMutablePath()
        for command in raw as? [[Any]] ?? [] {
            let n = command.dropFirst().compactMap { ($0 as? NSNumber)?.doubleValue }
            switch command.first as? String {
            case "M" where n.count == 2: path.move(to: CGPoint(x: n[0], y: n[1]))
            case "L" where n.count == 2: path.addLine(to: CGPoint(x: n[0], y: n[1]))
            case "C" where n.count == 6: path.addCurve(to: CGPoint(x:n[4],y:n[5]), control1: CGPoint(x:n[0],y:n[1]), control2: CGPoint(x:n[2],y:n[3]))
            case "Q" where n.count == 4: path.addQuadCurve(to: CGPoint(x:n[2],y:n[3]), control: CGPoint(x:n[0],y:n[1]))
            case "Z": path.closeSubpath()
            default: break
            }
        }
        return path
    }
    static let data: [String: Any]? = {
        guard let url = Bundle.main.url(forResource: "kastention-clock-v4.2", withExtension: "json"), let data = try? Data(contentsOf: url) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }()
    static func splines(_ raw: Any?) -> [CAMediaTimingFunction] {
        (raw as? [[Double]] ?? []).compactMap { v in v.count == 4 ? CAMediaTimingFunction(controlPoints:Float(v[0]),Float(v[1]),Float(v[2]),Float(v[3])) : nil }
    }
}

@objc(InkKastentionClock)
final class InkKastentionClockManager: RCTViewManager {
    override static func requiresMainQueueSetup() -> Bool { true }
    override func view() -> UIView! { InkKastentionClockView() }
}

final class InkKastentionClockView: UIView {
    @objc var enabled: Bool = false { didSet { observeVisibility() } }
    @objc var clockMode: String = "happy" { didSet { updateMode() } }
    @objc var faceMood: String = "happy" { didSet { updateMode() } }
    @objc var colorInk: UIColor = .label { didSet { updateColors() } }
    @objc var colorMinute: UIColor = .secondaryLabel { didSet { updateColors() } }
    @objc var colorSecond: UIColor = .systemBlue { didSet { updateColors() } }
    @objc var colorPaper: UIColor = .systemBackground { didSet { updateColors() } }
    private let art = ClockVector.data
    private let drawing = CALayer(), hands = CALayer()
    private var shapes: [CAShapeLayer] = [], hair: [(CAShapeLayer, [CGPath], [NSNumber], [CAMediaTimingFunction])] = []
    private var pointers: [CAShapeLayer] = [], markers: [(Int, CAShapeLayer)] = []
    private let pivot = CAShapeLayer(), reading = CATextLayer()
    private var timer: Timer?, previous: InkClockTime?, running = false
    private var tokens: [NSObjectProtocol] = []
    private var sad = false

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .clear; isOpaque = false; isUserInteractionEnabled = false
        if art == nil {
            let image = UIImageView(image: UIImage(named: "StartupArtwork"))
            image.contentMode = .scaleAspectFit; image.frame = bounds; image.autoresizingMask = [.flexibleWidth,.flexibleHeight]; addSubview(image)
            return
        }
        layer.addSublayer(drawing); drawing.anchorPoint = .zero
        makeLayers(); updateColors(); updateMode()
        for name in [UIApplication.didBecomeActiveNotification, UIApplication.didEnterBackgroundNotification, UIAccessibility.reduceMotionStatusDidChangeNotification] {
            tokens.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.observeVisibility() }
            })
        }
    }
    required init?(coder: NSCoder) { fatalError("Use the RN view manager") }
    deinit { timer?.invalidate(); for token in tokens { NotificationCenter.default.removeObserver(token) } }
    override func didMoveToWindow() { super.didMoveToWindow(); observeVisibility() }
    override func layoutSubviews() {
        super.layoutSubviews()
        let size = art?["size"] as? Double ?? 1254
        let scale = min(bounds.width / size, bounds.height / size)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        drawing.bounds = CGRect(x:0,y:0,width:size,height:size)
        drawing.position = CGPoint(x:(bounds.width-size*scale)/2,y:(bounds.height-size*scale)/2)
        drawing.setAffineTransform(CGAffineTransform(scaleX:scale,y:scale))
        CATransaction.commit()
    }
    private func makeLayers() {
        guard let art else { return }
        for (i, raw) in (art["paths"] as? [[String:Any]] ?? []).enumerated() {
            let shape = CAShapeLayer(); shape.path = ClockVector.path(raw["commands"])
            shape.lineWidth = raw["strokeWidth"] as? Double ?? 0; shape.lineCap = .round; shape.lineJoin = .round
            drawing.addSublayer(shape); shapes.append(shape)
            if let frames = raw["keyframes"] as? [Any], i > 0 {
                hair.append((shape,frames.map(ClockVector.path),(raw["keyTimes"] as? [Double] ?? []).map { NSNumber(value:$0) },ClockVector.splines(raw["splines"])))
            }
        }
        drawing.addSublayer(hands)
        for raw in art["hands"] as? [[String:Any]] ?? [] {
            let shape = CAShapeLayer(), path = CGMutablePath()
            path.move(to: CGPoint(x:0,y:(raw["fromY"] as? Double ?? 650)-650)); path.addLine(to: CGPoint(x:0,y:(raw["toY"] as? Double ?? 650)-650))
            shape.path = path; shape.position = CGPoint(x:625,y:650); shape.lineWidth = raw["width"] as? Double ?? 0; shape.lineCap = .round; shape.fillColor = nil
            hands.addSublayer(shape); pointers.append(shape)
        }
        pivot.path = CGPath(ellipseIn: CGRect(x:612,y:637,width:26,height:26), transform: nil); pivot.lineWidth = 9; hands.addSublayer(pivot)
        for mark in art["marks"] as? [[String:Any]] ?? [] {
            guard let center = mark["center"] as? [Double], center.count == 2 else { continue }
            let group = CALayer(), size = art["markSize"] as? Double ?? 48
            group.position = CGPoint(x:center[0]-size/2,y:center[1]-size/2); group.setAffineTransform(CGAffineTransform(scaleX:size/24,y:size/24)); drawing.addSublayer(group)
            for part in mark["parts"] as? [[String:Any]] ?? [] {
                let shape = CAShapeLayer()
                if let c = part["circle"] as? [Double], c.count == 3 { shape.path = CGPath(ellipseIn:CGRect(x:c[0]-c[2],y:c[1]-c[2],width:c[2]*2,height:c[2]*2), transform:nil) }
                else { shape.path = ClockVector.path(part["commands"]) }
                shape.lineWidth = 1.55; shape.lineCap = .round; shape.lineJoin = .round
                shape.fillColor = (part["fill"] as? String) == "none" ? nil : colorMinute.cgColor
                shape.strokeColor = (part["stroke"] as? String) == "none" ? nil : colorMinute.cgColor
                group.addSublayer(shape); markers.append((mark["hour"] as? Int ?? 0,shape))
            }
        }
        reading.alignmentMode = .center; reading.contentsScale = UIScreen.main.scale
        reading.font = UIFont.monospacedDigitSystemFont(ofSize:50,weight:.regular); reading.fontSize = 50
        reading.frame = CGRect(x:0,y:1140,width:1254,height:80); drawing.addSublayer(reading)
    }
    private func hex(_ value: String) -> CGColor? {
        if value == "none" { return nil }; if value == "currentColor" { return colorInk.cgColor }
        guard let n = UInt64(value.replacingOccurrences(of:"#",with:""),radix:16) else { return nil }
        return UIColor(red:Double((n>>16)&255)/255,green:Double((n>>8)&255)/255,blue:Double(n&255)/255,alpha:1).cgColor
    }
    private func updateColors() {
        CATransaction.begin(); CATransaction.setDisableActions(true)
        let raw = art?["paths"] as? [[String:Any]] ?? []
        for (i, shape) in shapes.enumerated() where raw.indices.contains(i) { shape.fillColor = hex(raw[i]["fill"] as? String ?? "none"); shape.strokeColor = hex(raw[i]["stroke"] as? String ?? "none") }
        for (i, shape) in pointers.enumerated() { shape.strokeColor = [colorInk,colorMinute,colorSecond][i].cgColor }
        pivot.fillColor = colorInk.cgColor; pivot.strokeColor = colorPaper.cgColor; reading.foregroundColor = colorMinute.cgColor
        for (_,shape) in markers { if shape.fillColor != nil { shape.fillColor = colorMinute.cgColor }; if shape.strokeColor != nil { shape.strokeColor = colorMinute.cgColor } }
        CATransaction.commit()
    }
    private func updateMode() {
        guard shapes.count == 7, let art else { return }
        let nextSad = clockMode == "sad" || (clockMode == "clock" && faceMood == "sad")
        let target = nextSad ? ClockVector.path(art["sadMouth"]) : ClockVector.path((art["paths"] as? [[String:Any]])?[6]["commands"])
        let old = shapes[6].presentation()?.path ?? shapes[6].path
        CATransaction.begin(); CATransaction.setDisableActions(true)
        hands.opacity = clockMode == "clock" ? 1 : 0; reading.isHidden = clockMode != "clock"
        for i in 4...6 { shapes[i].opacity = clockMode == "clock" ? 0.11 : 1 }
        shapes[6].path = target; CATransaction.commit()
        if running && nextSad != sad && !UIAccessibility.isReduceMotionEnabled {
            let animation = CABasicAnimation(keyPath:"path"); animation.fromValue = old; animation.toValue = target; animation.duration = art["mouthDuration"] as? Double ?? 0.29
            animation.timingFunction = CAMediaTimingFunction(controlPoints:0.25,0,0.25,1); shapes[6].add(animation,forKey:"mouth")
        }
        sad = nextSad
    }
    private func observeVisibility() {
        timer?.invalidate(); timer = nil
        running = enabled && window != nil && UIApplication.shared.applicationState == .active
        for layer in shapes + pointers { layer.removeAllAnimations() }
        previous = nil
        if running { tick(); schedule() }
    }
    private func schedule() {
        guard running else { return }
        let ms = Date().timeIntervalSince1970*1000
        let delay = (1000-ms.truncatingRemainder(dividingBy:1000)+(art?["tickOffsetMs"] as? Double ?? 4))/1000
        let next = Timer(timeInterval:delay,repeats:false) { [weak self] _ in MainActor.assumeIsolated { self?.tick(); self?.schedule() } }
        timer = next; RunLoop.main.add(next,forMode:.common)
    }
    private func tick() {
        guard let art, running else { return }
        let now = Date(), time = InkClockTime(now), steps = time.steps(after:previous), angles = time.angles
        let defs = art["hands"] as? [[String:Any]] ?? []
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for (i,shape) in pointers.enumerated() {
            shape.setAffineTransform(CGAffineTransform(rotationAngle:angles[i]*Double.pi/180))
            if let steps, steps[i], !UIAccessibility.isReduceMotionEnabled, clockMode == "clock", let before = previous, defs.indices.contains(i) {
                let start = before.angles[i], step = defs[i]["step"] as? Double ?? 0
                let animation = CAKeyframeAnimation(keyPath:"transform.rotation.z")
                animation.values = (art["handFractions"] as? [Double] ?? []).map { (start+$0*step)*Double.pi/180 }
                animation.keyTimes = (art["handKeyTimes"] as? [Double] ?? []).map { NSNumber(value:$0) }
                animation.timingFunctions = ClockVector.splines(art["handSplines"]); animation.duration = defs[i]["duration"] as? Double ?? 0
                shape.add(animation,forKey:"tick")
            }
        }
        reading.string = String(format:"%02d:%02d:%02d",time.hour,time.minute,time.second)
        CATransaction.commit()
        if steps != nil && !UIAccessibility.isReduceMotionEnabled {
            for (layer,frames,times,splines) in hair {
                let animation = CAKeyframeAnimation(keyPath:"path"); animation.values = frames; animation.keyTimes = times; animation.timingFunctions = splines; animation.duration = art["hairDuration"] as? Double ?? 0.52
                layer.add(animation,forKey:"hair")
            }
        }
        previous = time
    }
}
