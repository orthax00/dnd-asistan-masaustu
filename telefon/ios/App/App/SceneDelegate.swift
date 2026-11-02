import UIKit
import Capacitor

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }

        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = CAPBridgeViewController()
        window?.makeKeyAndVisible()

        SceneDelegateProxy.shared.scene(scene, willConnectTo: session, options: connectionOptions)
        if let url = connectionOptions.urlContexts.first?.url { girisBaglantisi(url) }
    }

    /// E-postadaki giriş linki dndasistani://giris?code=... ile uygulamayı açar → https://site/auth/callback?code=...
    private func girisBaglantisi(_ url: URL) {
        guard url.scheme == "dndasistani", url.host == "giris",
              var parcalar = URLComponents(string: "https://dnd-asistan.vercel.app/auth/callback") else { return }
        parcalar.percentEncodedQuery = URLComponents(url: url, resolvingAgainstBaseURL: false)?.percentEncodedQuery
        guard let adres = parcalar.url else { return }
        DispatchQueue.main.async {
            (self.window?.rootViewController as? CAPBridgeViewController)?.webView?.load(URLRequest(url: adres))
        }
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        if let url = URLContexts.first?.url { girisBaglantisi(url) }
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }
}
