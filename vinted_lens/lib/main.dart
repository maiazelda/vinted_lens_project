// lib/main.dart
// TOUS LES IMPORTS EN HAUT ⬇️

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'screens/visual_search_screen.dart';

void main() {
  runApp(const VintedLensApp());
}

class VintedLensApp extends StatelessWidget {
  const VintedLensApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vinted Lens',
      theme: ThemeData(
        primarySwatch: Colors.teal,
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.teal,
          foregroundColor: Colors.white,
        ),
      ),
      home: const VintedLensHome(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class VintedLensHome extends StatelessWidget {
  const VintedLensHome({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("🔍 Vinted Lens"),
        centerTitle: true,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.teal.shade50, Colors.white],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header
                Card(
                  elevation: 4,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: const Padding(
                    padding: EdgeInsets.all(20),
                    child: Column(
                      children: [
                        Icon(
                          Icons.camera_alt,
                          size: 60,
                          color: Colors.teal,
                        ),
                        SizedBox(height: 15),
                        Text(
                          "Recherche Visuelle Mode",
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF00695C),
                          ),
                        ),
                        SizedBox(height: 10),
                        Text(
                          "Scannez un vêtement et trouvez des articles similaires sur Vinted, Amazon et plus !",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 16,
                            color: Color(0xFF616161),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                
                const SizedBox(height: 30),
                
                // Bouton principal
                ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => VisualSearchScreen(),
                      ),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.teal,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 4,
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.search, size: 28),
                      SizedBox(width: 10),
                      Text(
                        "Commencer la Recherche",
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 20),
                
                // Fonctionnalités
                Card(
                  elevation: 2,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Padding(
                    padding: EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "✨ Fonctionnalités",
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 10),
                        _FeatureItem(icon: "🔍", text: "Recherche IA en <500ms"),
                        _FeatureItem(icon: "🛍️", text: "Multi-plateformes (Vinted, Amazon...)"),
                        _FeatureItem(icon: "📱", text: "Interface intuitive"),
                        _FeatureItem(icon: "⚡", text: "Résultats temps réel"),
                      ],
                    ),
                  ),
                ),
                
                const Spacer(),
                
                // Status API
                FutureBuilder<bool>(
                  future: _checkApiHealth(),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          SizedBox(width: 8),
                          Text("Vérification API..."),
                        ],
                      );
                    }
                    
                    bool isHealthy = snapshot.data ?? false;
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: isHealthy ? Colors.green.shade50 : Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isHealthy ? Colors.green : Colors.red,
                          width: 1,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            isHealthy ? Icons.check_circle : Icons.error,
                            color: isHealthy ? Colors.green : Colors.red,
                            size: 16,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            isHealthy ? "API Opérationnelle" : "API Non Disponible",
                            style: TextStyle(
                              color: isHealthy ? Colors.green.shade800 : Colors.red.shade800,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
  
  Future<bool> _checkApiHealth() async {
    try {
      final response = await http.get(Uri.parse('http://localhost:8000/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}

// Widget helper pour les fonctionnalités
class _FeatureItem extends StatelessWidget {
  final String icon;
  final String text;
  
  const _FeatureItem({required this.icon, required this.text});
  
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(icon, style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 10),
          Text(text, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
}