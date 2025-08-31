import 'dart:io';
import 'package:flutter/material.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isSearching = false;
  String _status = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        title: const Text(
          'Vinted Lens',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFF09B1BA),
        elevation: 0,
        centerTitle: true,
      ),
      body: Column(
        children: [
          // Header avec statut
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Color(0xFF09B1BA),
              borderRadius: BorderRadius.only(
                bottomLeft: Radius.circular(30),
                bottomRight: Radius.circular(30),
              ),
            ),
            child: Column(
              children: [
                const Icon(
                  Icons.camera_alt,
                  color: Colors.white,
                  size: 48,
                ),
                const SizedBox(height: 12),
                const Text(
                  'Scannez un vêtement',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Recherche LSH ultra-rapide < 50ms',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 16,
                  ),
                ),
                if (_status.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _status,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          const SizedBox(height: 40),
          
          // Boutons d'action
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                // Bouton Caméra
                _buildActionButton(
                  icon: Icons.camera_alt,
                  title: 'Prendre une photo',
                  subtitle: 'Scanner avec l\'appareil photo',
                  onTap: _takePhoto,
                ),
                
                const SizedBox(height: 16),
                
                // Bouton Galerie
                _buildActionButton(
                  icon: Icons.photo_library,
                  title: 'Choisir une photo',
                  subtitle: 'Sélectionner depuis la galerie',
                  onTap: _pickFromGallery,
                ),
              ],
            ),
          ),
          
          const Spacer(),
          
          // Zone de résultats (vide pour l'instant)
          Container(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Icon(
                  Icons.search,
                  size: 64,
                  color: Colors.grey.withOpacity(0.5),
                ),
                const SizedBox(height: 16),
                Text(
                  'Prêt pour la recherche',
                  style: TextStyle(
                    fontSize: 18,
                    color: Colors.grey.withOpacity(0.7),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Backend à connecter prochainement',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey.withOpacity(0.5),
                  ),
                ),
              ],
            ),
          ),
          
          const Spacer(),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: _isSearching ? null : onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF09B1BA).withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: const Color(0xFF09B1BA),
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
            if (_isSearching)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(Color(0xFF09B1BA)),
                ),
              )
            else
              const Icon(
                Icons.arrow_forward_ios,
                color: Colors.grey,
                size: 16,
              ),
          ],
        ),
      ),
    );
  }

  void _takePhoto() {
    setState(() {
      _isSearching = true;
      _status = 'Fonctionnalité bientôt disponible';
    });
    
    // Simuler un délai
    Future.delayed(const Duration(seconds: 2), () {
      setState(() {
        _isSearching = false;
        _status = 'Backend en cours de développement';
      });
    });
  }

  void _pickFromGallery() {
    setState(() {
      _isSearching = true;
      _status = 'Fonctionnalité bientôt disponible';
    });
    
    // Simuler un délai
    Future.delayed(const Duration(seconds: 2), () {
      setState(() {
        _isSearching = false;
        _status = 'Backend en cours de développement';
      });
    });
  }
}