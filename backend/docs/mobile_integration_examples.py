"""
=============================================================================
EXEMPLE D'INTÉGRATION CLIENT MOBILE
=============================================================================

Ce fichier montre comment intégrer l'API depuis :
- Une application Flutter/Dart
- Une application React Native
- Une application native Android (Kotlin)
- Une application native iOS (Swift)

Ces exemples sont à adapter selon votre framework mobile.

=============================================================================
"""

# =============================================================================
# FLUTTER / DART
# =============================================================================
FLUTTER_EXAMPLE = """
// pubspec.yaml - Ajouter la dépendance http
// dependencies:
//   http: ^1.1.0

import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiService {
  static const String baseUrl = 'http://VOTRE_IP:8000';
  
  // Health check
  static Future<bool> checkHealth() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  // Upload et traitement d'un fichier
  static Future<Map<String, dynamic>?> processFile(File file) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/process'));
      request.files.add(await http.MultipartFile.fromPath('file', file.path));
      
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      print('Erreur: $e');
      return null;
    }
  }
}

// Utilisation dans un widget
// final result = await ApiService.processFile(selectedFile);
// if (result != null && result['success']) {
//   // Afficher le résultat
// }
"""

# =============================================================================
# REACT NATIVE
# =============================================================================
REACT_NATIVE_EXAMPLE = """
// api.js
const BASE_URL = 'http://VOTRE_IP:8000';

// Health check
export const checkHealth = async () => {
  try {
    const response = await fetch(`${BASE_URL}/health`);
    return response.ok;
  } catch (error) {
    return false;
  }
};

// Upload et traitement d'un fichier
export const processFile = async (fileUri, fileName) => {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: fileName,
    type: 'application/octet-stream',
  });

  try {
    const response = await fetch(`${BASE_URL}/process`, {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (error) {
    console.error('Erreur:', error);
    return null;
  }
};

// Utilisation avec expo-document-picker
// import * as DocumentPicker from 'expo-document-picker';
// const result = await DocumentPicker.getDocumentAsync({});
// if (result.type === 'success') {
//   const apiResult = await processFile(result.uri, result.name);
// }
"""

# =============================================================================
# ANDROID KOTLIN
# =============================================================================
KOTLIN_EXAMPLE = """
// build.gradle - Ajouter les dépendances
// implementation 'com.squareup.okhttp3:okhttp:4.12.0'
// implementation 'com.google.code.gson:gson:2.10.1'

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.IOException

class ApiService {
    private val client = OkHttpClient()
    private val baseUrl = "http://VOTRE_IP:8000"
    
    // Health check
    fun checkHealth(): Boolean {
        val request = Request.Builder()
            .url("$baseUrl/health")
            .build()
        
        return try {
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: IOException) {
            false
        }
    }
    
    // Upload et traitement d'un fichier
    fun processFile(file: File, callback: (String?) -> Unit) {
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "file",
                file.name,
                file.asRequestBody("application/octet-stream".toMediaType())
            )
            .build()
        
        val request = Request.Builder()
            .url("$baseUrl/process")
            .post(requestBody)
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(null)
            }
            
            override fun onResponse(call: Call, response: Response) {
                callback(response.body?.string())
            }
        })
    }
}

// Utilisation dans une Activity/Fragment
// val apiService = ApiService()
// apiService.processFile(selectedFile) { result ->
//     runOnUiThread {
//         // Afficher le résultat
//     }
// }
"""

# =============================================================================
# iOS SWIFT
# =============================================================================
SWIFT_EXAMPLE = """
import Foundation

class ApiService {
    static let baseUrl = "http://VOTRE_IP:8000"
    
    // Health check
    static func checkHealth(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "\\(baseUrl)/health") else {
            completion(false)
            return
        }
        
        URLSession.shared.dataTask(with: url) { _, response, error in
            let httpResponse = response as? HTTPURLResponse
            completion(httpResponse?.statusCode == 200)
        }.resume()
    }
    
    // Upload et traitement d'un fichier
    static func processFile(fileURL: URL, completion: @escaping (Result<[String: Any], Error>) -> Void) {
        guard let url = URL(string: "\\(baseUrl)/process") else {
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\\(boundary)", forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        let filename = fileURL.lastPathComponent
        
        // Lire le fichier
        guard let fileData = try? Data(contentsOf: fileURL) else {
            return
        }
        
        // Construire le body multipart
        body.append("--\\(boundary)\\r\\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\\"file\\"; filename=\\"\\(filename)\\"\\r\\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\\r\\n\\r\\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\\r\\n--\\(boundary)--\\r\\n".data(using: .utf8)!)
        
        request.httpBody = body
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return
            }
            
            completion(.success(json))
        }.resume()
    }
}

// Utilisation dans un ViewController
// ApiService.processFile(fileURL: selectedFileURL) { result in
//     DispatchQueue.main.async {
//         switch result {
//         case .success(let json):
//             // Afficher le résultat
//         case .failure(let error):
//             // Gérer l'erreur
//         }
//     }
// }
"""

# =============================================================================
# CONFIGURATION RÉSEAU
# =============================================================================
NETWORK_CONFIG = """
CONFIGURATION RÉSEAU POUR LE DÉVELOPPEMENT
===========================================

Pour connecter votre app mobile au backend :

1. MÊME RÉSEAU WIFI
   - Le téléphone et l'ordinateur doivent être sur le même réseau WiFi
   - Remplacez 'localhost' par l'IP de votre machine

2. TROUVER VOTRE IP
   Windows : ipconfig | findstr IPv4
   Mac/Linux : ifconfig | grep inet
   
3. CONFIGURER LE SERVEUR
   Le serveur doit écouter sur 0.0.0.0 (toutes interfaces), pas 127.0.0.1
   C'est déjà configuré dans main.py

4. PARE-FEU
   Autorisez le port 8000 dans votre pare-feu
   Windows : netsh advfirewall firewall add rule name="API Dev" dir=in action=allow protocol=TCP localport=8000

5. ANDROID
   Si vous utilisez un émulateur Android :
   - Utilisez 10.0.2.2 au lieu de localhost (c'est l'hôte depuis l'émulateur)

6. iOS
   Dans Info.plist, autorisez les connexions non-HTTPS pour le développement :
   <key>NSAppTransportSecurity</key>
   <dict>
       <key>NSAllowsArbitraryLoads</key>
       <true/>
   </dict>
   
   ⚠️ À retirer en production !

7. PRODUCTION
   - Utilisez HTTPS
   - Configurez un vrai domaine
   - Utilisez un reverse proxy (nginx, traefik)
"""

if __name__ == "__main__":
    print("=" * 60)
    print("EXEMPLES D'INTÉGRATION MOBILE")
    print("=" * 60)
    print("\nCe fichier contient des exemples de code pour :")
    print("- Flutter/Dart")
    print("- React Native")
    print("- Android Kotlin")
    print("- iOS Swift")
    print("\nConsultez le code source pour les exemples détaillés.")
    print("\n" + NETWORK_CONFIG)
