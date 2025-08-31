// lib/screens/visual_search_screen.dart
// Version compatible Flutter Web

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;

class VisualSearchScreen extends StatefulWidget {
  @override
  _VisualSearchScreenState createState() => _VisualSearchScreenState();
}

class _VisualSearchScreenState extends State<VisualSearchScreen> {
  XFile? _selectedImage;
  Uint8List? _imageBytes;
  bool _isLoading = false;
  bool _isProcessing = false;
  List<SearchResult> _results = [];
  String _statusMessage = "";
  double? _processingTime;

  final ImagePicker _picker = ImagePicker();
  final String apiBaseUrl = "http://localhost:8000";

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("🔍 Vinted Lens"),
        backgroundColor: Colors.teal,
        foregroundColor: Colors.white,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.teal.shade50, Colors.white],
          ),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Section Upload Image
              _buildImageSection(),
              
              const SizedBox(height: 20),
              
              // Boutons d'action
              _buildActionButtons(),
              
              const SizedBox(height: 20),
              
              // Status et Processing Time
              if (_statusMessage.isNotEmpty) _buildStatusSection(),
              
              const SizedBox(height: 20),
              
              // Résultats de recherche
              if (_results.isNotEmpty) _buildResultsSection(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildImageSection() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Text(
              "📸 Sélectionnez un Vêtement",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 15),
            
            // Zone d'affichage de l'image
            Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300, width: 2),
                borderRadius: BorderRadius.circular(10),
                color: Colors.grey.shade50,
              ),
              child: _imageBytes != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.memory(
                        _imageBytes!,
                        fit: BoxFit.cover,
                      ),
                    )
                  : const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.image, size: 50, color: Colors.grey),
                        SizedBox(height: 10),
                        Text(
                          "Aucune image sélectionnée",
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Row(
      children: [
        // Bouton Caméra (désactivé sur Web)
        Expanded(
          child: ElevatedButton.icon(
            onPressed: kIsWeb || _isLoading ? null : () => _pickImage(ImageSource.camera),
            icon: const Icon(Icons.camera_alt),
            label: Text(kIsWeb ? "Caméra (N/A Web)" : "Caméra"),
            style: ElevatedButton.styleFrom(
              backgroundColor: kIsWeb ? Colors.grey : Colors.blue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ),
        
        const SizedBox(width: 10),
        
        // Bouton Galerie (fonctionne sur Web)
        Expanded(
          child: ElevatedButton.icon(
            onPressed: _isLoading ? null : () => _pickImage(ImageSource.gallery),
            icon: const Icon(Icons.photo_library),
            label: const Text("Galerie"),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatusSection() {
    return Card(
      color: _isProcessing ? Colors.blue.shade50 : Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Row(
          children: [
            if (_isProcessing) 
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              const Icon(Icons.check_circle, color: Colors.green),
            
            const SizedBox(width: 10),
            
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_statusMessage, style: const TextStyle(fontWeight: FontWeight.w500)),
                  if (_processingTime != null)
                    Text(
                      "⚡ Traité en ${_processingTime!.toStringAsFixed(3)}s",
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsSection() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "🎯 Résultats Similaires (${_results.length})",
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 15),
            
            ...(_results.map((result) => _buildResultItem(result)).toList()),
          ],
        ),
      ),
    );
  }

  Widget _buildResultItem(SearchResult result) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(
            result.imageUrl,
            width: 60,
            height: 60,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return Container(
                width: 60,
                height: 60,
                color: Colors.grey.shade200,
                child: const Icon(Icons.image_not_supported),
              );
            },
          ),
        ),
        title: Text(result.title, style: const TextStyle(fontWeight: FontWeight.w500)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("${result.price} • ${result.platform}"),
            const SizedBox(height: 2),
            Row(
              children: [
                const Icon(Icons.favorite, size: 14, color: Colors.red),
                const SizedBox(width: 4),
                Text(
                  "${(result.similarity * 100).toInt()}% similaire",
                  style: TextStyle(
                    color: result.similarity > 0.8 ? Colors.green : 
                           result.similarity > 0.6 ? Colors.orange : Colors.grey,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ),
        trailing: const Icon(Icons.arrow_forward_ios),
        onTap: () {
          _showItemDetails(result);
        },
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? image = await _picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );

      if (image != null) {
        // Lire les bytes de l'image pour l'affichage Web
        final Uint8List imageBytes = await image.readAsBytes();
        
        setState(() {
          _selectedImage = image;
          _imageBytes = imageBytes;
          _results.clear();
          _statusMessage = "Image sélectionnée - Prête pour la recherche";
        });
        
        // Lancer automatiquement la recherche
        await _performVisualSearch();
      }
    } catch (e) {
      _showError("Erreur lors de la sélection: $e");
    }
  }

  Future<void> _performVisualSearch() async {
    if (_selectedImage == null) return;

    setState(() {
      _isProcessing = true;
      _statusMessage = "🔍 Recherche en cours...";
      _results.clear();
    });

    try {
      print("Début de la recherche visuelle");
      
      // Préparer la requête multipart
      final uri = Uri.parse('$apiBaseUrl/api/search-similar');
      final request = http.MultipartRequest('POST', uri);
      
      // Lire les bytes de l'image
      final bytes = await _selectedImage!.readAsBytes();
      print("Image lue: ${bytes.length} bytes");
      
      // Ajouter le fichier à la requête
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: _selectedImage!.name,
      ));

      print("Envoi de la requête...");
      
      // Envoyer la requête avec timeout
      final response = await request.send().timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Timeout: Le serveur met trop de temps à répondre');
        },
      );
      
      print("Réponse reçue: ${response.statusCode}");
      
      if (response.statusCode == 200) {
        final responseBody = await response.stream.bytesToString();
        final int maxPreview = 200;
        final int end = responseBody.length < maxPreview ? responseBody.length : maxPreview;
        final String preview = responseBody.isEmpty ? "" : responseBody.substring(0, end);print("Corps de la réponse: $preview...");
        
        final jsonData = json.decode(responseBody);
        
        setState(() {
          _processingTime = jsonData['processing_time']?.toDouble();
          _statusMessage = "✅ Recherche terminée - ${jsonData['total_results']} résultats trouvés";
          
          _results = (jsonData['results'] as List)
              .map((item) => SearchResult.fromJson(item))
              .toList();
        });
        
        print("Résultats traités: ${_results.length}");
        
      } else {
        final errorBody = await response.stream.bytesToString();
        print("Erreur ${response.statusCode}: $errorBody");
        throw Exception('Erreur API ${response.statusCode}: $errorBody');
      }
      
    } catch (e) {
      print("Exception dans _performVisualSearch: $e");
      _showError("Erreur recherche: $e");
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  void _showItemDetails(SearchResult result) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(result.title),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(
                result.imageUrl,
                height: 150,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 10),
            Text("💰 Prix: ${result.price}"),
            Text("🏪 Plateforme: ${result.platform}"),
            Text("❤️ Similarité: ${(result.similarity * 100).toInt()}%"),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Fermer"),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Ouvrir le lien externe
              Navigator.pop(context);
            },
            child: const Text("Voir l'Article"),
          ),
        ],
      ),
    );
  }

  void _showError(String message) {
    setState(() {
      _statusMessage = "❌ $message";
      _isProcessing = false;
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}

// Modèle de données pour les résultats
class SearchResult {
  final int id;
  final String title;
  final double price;
  final String platform;
  final String url;
  final String imageUrl;
  final double similarity;

  SearchResult({
    required this.id,
    required this.title,
    required this.price,
    required this.platform,
    required this.url,
    required this.imageUrl,
    required this.similarity,
  });

  factory SearchResult.fromJson(Map<String, dynamic> json) {
    return SearchResult(
      id: json['id'],
      title: json['title'],
      price: json['price'].toDouble(),
      platform: json['platform'],
      url: json['url'],
      imageUrl: json['image'],
      similarity: json['similarity']?.toDouble() ?? 0.0,
    );
  }
}